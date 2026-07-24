from urllib.parse import quote
import requests

def send_otp_sms(mobile, otp):
    try:

        message = (
            f"Use OTP {otp} to login to VOCABBEE. "
            f"OTP is valid for 10 minutes. "
            f"Do not share this OTP with anyone."
        )

        url = (
            "https://full2ads.com/smsapi/index"
            f"?key=26911C63F0A654"
            f"&campaign=0"
            f"&routeid=1"
            f"&type=text"
            f"&contacts={mobile}"
            f"&senderid=VOCABE"
            f"&tlv=%7B%22DLT_ENTITY_ID%22%3A%221001548232379518414%22%2C%22DLT_TEMPLATE_ID%22%3A%221107178030754522073%22%7D"
            f"&msg={quote(message)}"
        )
        response = requests.get(
            url,
            timeout=10
        )
        print("SMS Response:", response.text)
        return True
    except Exception as e:
        print("SMS Error:", str(e))
        return False


def send_sms_to_mobile(var1, mobile, msg):
    try:




        url = "https://sms.lifeboattechnologies.com/dev/bulkV2"
        params = {
            "authorization": "CfnZkoK6sueIEU9GwL3BbiXgD8xluNQ0HlRTPrbzpSmVJ152O7tyWbQfSXVBO94Nra0DhHx6YkosTEzu",
            "route": "dlt",
            "sender_id": "VOCABE",      # VOCABE
            "message": msg,
            "variables_values": f"{var1}|",
            "flash": "0",
            "numbers": str(mobile)
        }
        print(params)
        response = requests.get(
            url,
            params=params,
            timeout=10
        )
        print(response)
        if response.status_code == 200:
            return True
        return False

    except Exception as e:
        print("Error sending OTP SMS:", str(e))
        return False
