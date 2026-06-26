import base64
import json

from firebase_admin import messaging
import firebase_admin
from firebase_admin import credentials
from django.conf import settings

from db.models import Devices


def init_firebase():
    if firebase_admin._apps:
        return

    firebase_config = json.loads(
        base64.b64decode(settings.FIREBASE_CREDENTIALS).decode("utf-8")
    )
    cred = credentials.Certificate(
        firebase_config
    )
    firebase_admin.initialize_app(cred)


def send_push_notification(
        user,
        notification_type,
        payload,
        priority="high"
):
    print("===== SENDING  NOTIFICATION =====")

    init_firebase()

    final_payload = {
        "type": notification_type,
        **payload
    }

    print(f"Payload: {final_payload}")

    devices = Devices.objects.filter(
        user=user,
        is_active=True,
        fcm_token__isnull=False
    ).exclude(fcm_token="")

    print(f"Total devices found: {devices.count()}")

    sent_count = 0

    for device in devices:

        print("================================")
        print(f"Device Session ID: {device.id}")
        print(f"Token: {device.fcm_token}")
        print(f"Platform: {device.platform}")
        try:
            message = messaging.Message(
                token=device.fcm_token,
                data={
                    key: (
                        json.dumps(value)
                        if isinstance(value, (dict, list))
                        else str(value)
                    )
                    for key, value in final_payload.items()
                },

                android=messaging.AndroidConfig(
                    priority=priority
                ),

                apns=messaging.APNSConfig(
                    headers={
                        "apns-priority": "5",
                    },
                    payload=messaging.APNSPayload(
                        aps=messaging.Aps(
                            content_available=True
                        )
                    ),
                )
            )

            print("===== FCM MESSAGE DETAILS =====")
            print(f"Payload: {final_payload}")
            print(f"Notification Type: {notification_type}")
            print("Contains notification payload: NO")
            print("Contains data payload: YES")
            print(f"Android priority: {priority}")

            response = messaging.send(message)

            print(f"Notification sent: {response}")
            sent_count += 1

        except Exception as e:
            print(f"FCM send failed: {str(e)}")

    return sent_count

############################################################
############################################################
### Push Notifications ==> notification + data messages  ###
############################################################
############################################################

def send_visible_push_notification(user,
                                   title,
                                   body,
                                   notification_type,
                                   payload=None,
                                   priority="high"):
    init_firebase()
    print("Firebase Initialized")
    payload = payload or {}
    final_payload = {
        "type": notification_type,
        **payload
    }
    print(final_payload)
    devices = Devices.objects.filter(
        user=user,is_active=True,fcm_token__isnull=False
    ).exclude(fcm_token="")
    sent_count = 0
    print("devices count with user and fcm not null is ====")
    print(devices)

    for device in devices:
        try:
            message = messaging.Message(
                token=device.fcm_token,
                notification=messaging.Notification(
                    title=title,
                    body=body
                ),
                data={
                    key: (
                        json.dumps(value)
                        if isinstance(value, (dict, list))
                        else str(value)
                    )
                    for key, value in final_payload.items()
                },
                android=messaging.AndroidConfig(
                    priority=priority,
                    notification=messaging.AndroidNotification(
                        channel_id="default"
                    )
                ),
                apns=messaging.APNSConfig(
                    headers={
                        "apns-priority": "10"
                    },
                    payload=messaging.APNSPayload(
                        aps=messaging.Aps(
                            sound="default",
                            badge=1
                        )
                    )
                )
            )
            messaging.send(message)
            sent_count += 1
            print("push sent")
            print(sent_count)
            print(device.fcm_token)
        except Exception as error:
            print(error)
            pass