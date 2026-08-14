import stripe
from django.conf import settings
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from django.shortcuts import redirect
from django.contrib.auth import get_user_model
from django.http import HttpResponse

stripe.api_key = getattr(settings, 'STRIPE_SECRET_KEY', None)
User = get_user_model()

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_checkout_session(request):
    user = request.user
    origin = request.META.get('HTTP_ORIGIN', 'http://localhost:5173')

    if stripe.api_key:
        try:
            checkout_session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=[
                    {
                        'price_data': {
                            'currency': 'inr',
                            'unit_amount': 150000, # 1500 INR
                            'product_data': {
                                'name': 'Vectra Pro Subscription',
                            },
                        },
                        'quantity': 1,
                    },
                ],
                mode='payment',
                success_url=origin + '/app?payment=success',
                cancel_url=origin + '/app/settings',
                client_reference_id=str(user.id),
                customer_email=user.email,
            )
            return Response({'url': checkout_session.url})
        except Exception as e:
            return Response({'error': str(e)}, status=400)
    else:
        # Mock checkout flow (Demo)
        mock_url = f"{request.build_absolute_uri('/api/payments/mock-success/')}?user_id={user.id}&origin={origin}"
        return Response({'url': mock_url})

@api_view(['GET'])
@permission_classes([AllowAny])
def mock_success(request):
    """
    In a real app this wouldn't exist, but for the demo this instantly upgrades
    the user and redirects them back to the frontend.
    """
    user_id = request.GET.get('user_id')
    origin = request.GET.get('origin', 'http://localhost:5173')
    if user_id:
        try:
            user = User.objects.get(id=user_id)
            user.plan = 'pro'
            user.save()
        except User.DoesNotExist:
            pass
    return redirect(f"{origin}/app?payment=success")

@api_view(['POST'])
@permission_classes([AllowAny])
def stripe_webhook(request):
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
    endpoint_secret = getattr(settings, 'STRIPE_WEBHOOK_SECRET', None)

    event = None
    if endpoint_secret and sig_header:
        try:
            event = stripe.Webhook.construct_event(payload, sig_header, endpoint_secret)
        except ValueError as e:
            return HttpResponse(status=400)
        except stripe.error.SignatureVerificationError as e:
            return HttpResponse(status=400)
    else:
        import json
        try:
            event = json.loads(payload)
        except json.JSONDecodeError:
            return HttpResponse(status=400)

    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        client_reference_id = session.get('client_reference_id')
        if client_reference_id:
            try:
                user = User.objects.get(id=client_reference_id)
                user.plan = 'pro'
                user.save()
            except User.DoesNotExist:
                pass

    return HttpResponse(status=200)
