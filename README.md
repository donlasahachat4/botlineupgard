# Bot Line Upgard

This repository contains a Flask based betting system that integrates with a
LINE Official Account.  The classic application works mainly through LINE chat
commands.  The new web interface is provided by *app.py* which loads all
blueprints and models for the MySQL backend.
front‑end and MySQL database.

## Running the integrated example

1. Create a MySQL database and import `schema.sql`.
2. Set the following environment variables before running the server:
   - `MYSQL_HOST`, `MYSQL_USER`, `MYSQL_PASS`, `MYSQL_DB`
   - `LINE_ACCESS_TOKEN` and `LINE_GROUP_ID`
   - `LINE_CLIENT_ID`, `LINE_CLIENT_SECRET`, `LINE_REDIRECT_URI`
   - `LINE_CHANNEL_ACCESS_TOKEN`, `LINE_CHANNEL_SECRET`
   - `STREAM_URL` (HLS URL for the live video, optional)
   - `ADMIN_TOKEN` (token for admin routes)
   - `BET_ALERT` (threshold for large bet alert)
   - `LOGO_TEXT` (displayed logo text on login pages)
  - `LINE_NOTIFY_TOKEN` (token for sending Line Notify messages)
  - `JWT_SECRET_KEY` (secret key for Flask JWT sessions)
  - `MIN_DEPOSIT` (minimum deposit amount in Baht)
  - `EASY_TOKEN` and `SLIP2GO_TOKEN` (tokens for slip verification services)
3. Install requirements (includes Flask-SQLAlchemy):

```bash
pip install -r requirements.txt
```

4. Start the application:

```bash
python3 app.py
```

Open `http://localhost:8000/` for the betting page and `http://localhost:8000/admin`
for the admin dashboard.  Bets and admin actions are broadcast in real time to all
connected clients and mirrored to the LINE group via the Messaging API.

### Manual test checklist

1. สมัครและล็อกอิน ผ่านหน้าเว็บ
2. ขอฝากเงินและให้แอดมินอนุมัติ/ปฏิเสธ ดูยอดเงินอัปเดต
3. ขอถอนเงินแล้วให้แอดมินอนุมัติ/ปฏิเสธ ตรวจสอบยอดคืน
4. เปิดรอบ ปิดรอบ และประกาศผลจากหน้าแอดมิน ดูว่าข้อความถูกส่งไปยังกลุ่ม LINE
5. วางเดิมพันจากเว็บและจาก LINE แล้วเช็คว่าทั้งสองฝั่งเห็นยอดแบบเรียลไทม์
6. ตรวจสอบหน้า /logs ว่ามีบันทึกทุกเหตุการณ์และดาวน์โหลด CSV ได้ (หากต้องการ)
7. เรียก `/api/health` เพื่อเช็กสถานะเซิร์ฟเวอร์ (ควรได้ `{"status": "ok"}`)
8. ใช้หน้า `/deposit` เพื่อสร้างคิวอาร์และโอนตามยอดที่แสดง
9. ส่งข้อความไปที่ `/api/admin/sms` เพื่อลองจับคู่ยอดฝากอัตโนมัติ
10. เปิดหน้า `/api/admin/deposit_logs` เพื่อตรวจสอบคำขอฝากแบบ PromptPay

The admin can also view system logs at `/logs` which lists bet, wallet, system and security logs for auditing purposes.

### Deployment notes

Run the app with a production WSGI server such as Gunicorn with eventlet for Socket.IO:

```bash
gunicorn -k eventlet -w 1 app:app
```

Ensure MySQL and LINE credentials are set in the environment and configure HTTPS and a reverse proxy if exposing publicly.

### Security & Access Checklist

- Unique phone number and LINE ID enforced
- Users cannot edit their info after registration
- Admin panel requires `ADMIN_TOKEN`
- All wallet and bet actions logged and append-only
- LINE/Web accounts share a single wallet when linked

### Deposit webhook integration

The endpoint `/webhook/deposit` accepts POST requests from SMS forwarders or
other services. Include a `message` field with the notification text. The server
records each notification and tries to match it to a pending deposit created via
the PromptPay QR flow. When a match occurs the wallet balance is credited and a
`deposit_matched` Socket.IO event is emitted.

Administrators configure tokens on the **Integrations** page (`/admin/integrations`).
Set webhook URLs for each channel there. Incoming messages are logged under
`/admin/integration-logs` and matched automatically when possible.
