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