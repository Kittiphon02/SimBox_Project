from services.sms_log import log_sms_sent, list_logs

log_sms_sent("0653988461", "กิตติภรณ์", "ส่งสำเร็จ")

rows = list_logs(direction="sent", limit=5)
for r in rows:
    print(r["id"], r["phone"], r["message"], r["status"], r["dt"])
