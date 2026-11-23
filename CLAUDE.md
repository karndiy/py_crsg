# CLAUDE.md
# Community Radio SMS Gateway – Offline Edition

**Project:** Community Radio SMS Gateway  
**Platform:** Raspberry Pi  
**Backend:** Python + Flask  
**Database:** SQLite  
**Hardware:** SIM7600 LTE Module  
**TTS Engine:** Piper Offline TTS  
**Language:** Thai / English  
**Deployment:** Local Raspberry Pi + LAN Dashboard  
**Announcement Mode:** Automatic  
**Communication Mode:** SMS + Phone Call

---

# 1. Project Overview

พัฒนาระบบวิทยุชุมชนอัตโนมัติ โดยใช้ Raspberry Pi เป็นศูนย์กลางรับข้อความ SMS และคำสั่งโทรศัพท์จากประชาชนหรือผู้ดูแลระบบ

ระบบต้องสามารถรับ SMS ผ่าน SIM7600 โดยไม่ต้องใช้อินเทอร์เน็ต นำข้อความมาตรวจสอบสิทธิ์ บันทึกลง SQLite แปลงข้อความภาษาไทยเป็นเสียงด้วย Piper TTS แบบ Offline และเล่นเสียงผ่านอุปกรณ์ Audio Output ไปยังเครื่องขยายเสียงและลำโพงชุมชน

ระบบต้องมี Web Dashboard สำหรับบริหารจัดการ และสามารถทำงานได้แม้ไม่มี WAN Internet

## Main Objectives

1. รับ SMS ผ่าน SIM7600 LTE Modem
2. รองรับข้อความภาษาไทยทั้ง UCS2 และ Multipart SMS
3. ตรวจสอบหมายเลขผู้ส่งด้วย Sender Whitelist
4. ตรวจสอบรูปแบบคำสั่งและ PIN/Secret
5. ประกาศข้อความอัตโนมัติเมื่อผ่านการตรวจสอบ
6. รองรับ Phone Call Command
7. ใช้ Piper TTS สร้างเสียงภาษาไทยแบบ Offline
8. เล่นเสียงผ่าน Raspberry Pi Audio Output
9. จัดเก็บข้อมูลทั้งหมดใน SQLite
10. จัดการระบบผ่าน Web Dashboard
11. รองรับการทำงานแบบ Local และ LAN
12. ออกแบบให้เพิ่มอุปกรณ์และช่องทางรับข้อความได้ในอนาคต

---

# 2. System Configuration

ค่าการทำงานหลักที่ต้องรักษาไว้:

| Configuration | Value |
|---|---|
| SMS Mode | sms-call |
| Announcement | auto |
| Dashboard | both |
| Backend | Flask |
| Database | SQLite |
| SMS Modem | SIM7600 |
| SMS Protocol | AT Commands |
| SMS Encoding | GSM-7 / UCS2 |
| TTS | Piper Offline |
| Audio Format | WAV |
| Audio Player | ALSA / aplay |
| Deployment | Raspberry Pi |
| Internet Required | No, for core operation |
| Dashboard Access | Localhost + LAN |

Configuration ควรจัดเก็บใน `.env` และไฟล์ Configuration แยกตามความเหมาะสม

ห้าม Hardcode รหัสผ่าน, PIN, API Key หรือข้อมูลสำคัญใน Source Code

---

# 3. Development Rules

Claude ต้องปฏิบัติตามกฎเหล่านี้ทุกครั้ง:

1. ตรวจสอบโครงสร้าง Project ก่อนแก้ไข
2. อ่าน Source Code เดิมและทำความเข้าใจ Workflow
3. ห้ามลบหรือเขียนทับระบบเดิมโดยไม่จำเป็น
4. ห้ามสร้างไฟล์ซ้ำซ้อนโดยไม่ตรวจสอบของเดิม
5. แยก Hardware Layer ออกจาก Business Logic
6. แยก SMS Gateway, TTS, Audio Player และ Flask API ออกจากกัน
7. ใช้ Python Type Hints เมื่อเหมาะสม
8. ใช้ Logging แทนการใช้ print ใน Production
9. จัดการ Exception ทุกจุดที่เกี่ยวข้องกับ Hardware
10. ใช้ Environment Variables สำหรับ Configuration
11. ต้องมี Unit Tests สำหรับ Logic สำคัญ
12. ต้องมี README สำหรับการติดตั้งและแก้ปัญหา
13. ต้องไม่สมมติว่า SIM7600 ใช้ Serial Port เดียวกันทุกเครื่อง
14. ต้องไม่สมมติว่าโมเด็มรองรับคำสั่ง AT ทุกคำสั่งเหมือนกัน
15. ทุกการเปลี่ยนแปลงต้องมีวิธีทดสอบและ Rollback

ก่อนพัฒนาแต่ละ Feature ให้รายงาน:
- ปัญหาหรือสิ่งที่ต้องเพิ่ม
- ไฟล์ที่จะเปลี่ยนแปลง
- แนวทางแก้ไข
- ความเสี่ยง
- Test Plan

---

# 4. System Architecture

ออกแบบระบบเป็น Modular Architecture

```text
                  MOBILE NETWORK
                         |
                         |
                  SIM7600 + SIM
                         |
                Raspberry Pi Serial
                         |
              +--------------------+
              |   SMS / CALL       |
              |   Gateway          |
              +--------------------+
                         |
              +--------------------+
              | Authentication     |
              | Sender Whitelist   |
              | Command Validator  |
              +--------------------+
                         |
              +--------------------+
              | Flask Application  |
              | Business Logic     |
              +--------------------+
                         |
                  SQLite Database
                         |
              +--------------------+
              | Announcement Queue |
              +--------------------+
                         |
              +--------------------+
              | Piper Thai TTS      |
              | Offline Engine      |
              +--------------------+
                         |
              +--------------------+
              | Audio Player        |
              | ALSA / aplay        |
              +--------------------+
                         |
                  Audio Amplifier
                         |
                  Community Speaker


              +--------------------+
              | Web Dashboard      |
              | Localhost + LAN    |
              +--------------------+
                         |
                     Flask API
```

## Architectural Requirements

- Flask ไม่ควรทำงานอ่าน Serial Port โดยตรงใน HTTP Request
- SMS Reader ต้องทำงานเป็น Background Service หรือ Worker
- Call Monitor ต้องแยกจาก SMS Reader
- TTS Worker ต้องแยกจาก Web Request
- Audio Queue ต้องป้องกันการเล่นเสียงซ้อนกัน
- Database ต้องรองรับการบันทึกสถานะและตรวจสอบย้อนหลัง
- Hardware Module ต้องสามารถ Mock ได้ใน Unit Tests

---

# 5. Recommended Project Structure

ตรวจสอบโครงสร้างจริงก่อน หากมีไฟล์เดิมอยู่แล้วให้ปรับจากของเดิม ไม่จำเป็นต้องสร้างใหม่ทั้งหมด

```text
community-radio/
│
├── app.py
├── config.py
├── extensions.py
├── requirements.txt
├── .env.example
├── .gitignore
├── CLAUDE.md
├── README.md
│
├── instance/
│   └── community_radio.db
│
├── models/
│   ├── sms_message.py
│   ├── authorized_sender.py
│   ├── announcement.py
│   ├── call_command.py
│   ├── audio_file.py
│   └── system_log.py
│
├── modules/
│   │
│   ├── sms_gateway/
│   │   ├── modem.py
│   │   ├── sms_reader.py
│   │   ├── pdu_decoder.py
│   │   ├── multipart.py
│   │   └── sender_validator.py
│   │
│   ├── call_gateway/
│   │   ├── call_monitor.py
│   │   ├── caller_validator.py
│   │   └── call_command.py
│   │
│   ├── announcement/
│   │   ├── processor.py
│   │   ├── queue.py
│   │   ├── scheduler.py
│   │   └── priority.py
│   │
│   ├── tts/
│   │   ├── piper_engine.py
│   │   └── audio_converter.py
│   │
│   ├── audio/
│   │   ├── audio_player.py
│   │   ├── device_manager.py
│   │   └── playback_queue.py
│   │
│   └── security/
│       ├── authentication.py
│       ├── api_key.py
│       ├── rate_limiter.py
│       └── command_validator.py
│
├── routes/
│   ├── dashboard.py
│   ├── api.py
│   ├── sms.py
│   ├── announcement.py
│   ├── sender.py
│   └── settings.py
│
├── services/
│   ├── sms_service.py
│   ├── call_service.py
│   ├── announcement_service.py
│   └── audio_service.py
│
├── templates/
│   ├── base.html
│   ├── dashboard.html
│   ├── inbox.html
│   ├── announcements.html
│   ├── senders.html
│   ├── calls.html
│   ├── audio.html
│   └── settings.html
│
├── static/
│   ├── css/
│   ├── js/
│   └── audio/
│
├── models_voice/
│   └── README.md
│
├── scripts/
│   ├── detect_modem.py
│   ├── test_sms.py
│   ├── test_call.py
│   ├── test_tts.py
│   ├── test_audio.py
│   └── create_admin.py
│
├── tests/
│   ├── test_pdu_decoder.py
│   ├── test_multipart.py
│   ├── test_sender_validator.py
│   ├── test_announcement.py
│   ├── test_call_gateway.py
│   └── test_api.py
│
├── logs/
│
└── systemd/
    ├── community-radio.service
    └── community-radio-worker.service
```

---

# 6. SIM7600 SMS Gateway

พัฒนาโมดูลสำหรับเชื่อมต่อ SIM7600 ผ่าน Serial AT Commands

## Required AT Commands

```text
AT
AT+CPIN?
AT+CSQ
AT+CREG?
AT+CMGF=1
AT+CNMI=2,1,0,0,0
```

การอ่าน SMS:

```text
AT+CMGR=<INDEX>
```

การลบ SMS:

```text
AT+CMGD=<INDEX>
```

ตรวจสอบการเชื่อมต่อ:

```text
AT+CSQ
AT+CPIN?
AT+CREG?
```

## SMS Reader Requirements

1. ตรวจสอบ Serial Port ก่อนเปิดใช้งาน
2. รองรับ Configurable Baud Rate
3. ตรวจสอบ SIM Ready
4. ตรวจสอบ Signal Quality
5. ตรวจสอบ Network Registration
6. รับ Event `+CMTI`
7. อ่าน SMS จาก Index
8. ส่ง SMS เข้า PDU Decoder เมื่อจำเป็น
9. บันทึกข้อมูลลง SQLite
10. ลบ SMS จาก Modem หลังบันทึกและประมวลผลสำเร็จ
11. มี Retry เมื่อ Serial Connection ขาด
12. มี Logging สำหรับ AT Command Error
13. ป้องกันการประมวลผล SMS ซ้ำ

ตัวอย่าง Notification:

```text
+CMTI: "SM",3
```

ระบบต้องอ่าน SMS Index 3 และจัดการข้อความต่อไป

## Important

ห้ามใช้ Serial Port เดียวกันจากหลาย Thread โดยไม่มี AT Command Lock

ต้องมี AT Command Manager เพื่อควบคุมการส่งคำสั่งและรับ Response

แยกการอ่าน SMS, การอ่านสถานะ Call และการส่ง AT Command อย่างปลอดภัย

ตรวจสอบพอร์ตจริงของ SIM7600 ก่อนกำหนดค่า เช่น `/dev/ttyUSB2` โดยห้ามยึดตัวอย่างนี้เป็นค่าตายตัว

---

# 7. Thai PDU Decoder

พัฒนา Decoder สำหรับข้อความ SMS ภาษาไทย

ต้องรองรับ:

- GSM 7-bit
- UCS2 / UTF-16BE
- SMS PDU Mode
- Sender Number
- Timestamp
- User Data Length
- User Data Header (UDH)
- Concatenated SMS
- Multipart Message Reassembly

## Multipart SMS

กรณีข้อความยาวถูกแบ่งหลาย SMS ต้องรวมข้อความให้สมบูรณ์ก่อนส่งไปยัง Announcement Processor

ใช้ข้อมูลต่อไปนี้ในการจัดกลุ่ม:

- Sender Number
- Concatenation Reference
- Total Segments
- Segment Sequence Number

ต้องกำหนด Timeout สำหรับข้อความที่มาไม่ครบทุก Segment และไม่ประกาศข้อความที่ยังประกอบไม่สมบูรณ์

สร้าง Unit Tests ด้วย PDU ตัวอย่างที่ตรวจสอบ Encoding ได้จริง

ห้ามเขียน Decoder โดยอาศัยการตัด String แบบคาดเดา

---

# 8. Sender Whitelist and Security

ระบบต้องไม่ประกาศ SMS จากบุคคลทั่วไปโดยอัตโนมัติ

อนุญาตเฉพาะหมายเลขโทรศัพท์ที่ลงทะเบียนใน Whitelist

## SMS Command Format

```text
RADIO#PIN#PRIORITY#MESSAGE
```

ตัวอย่าง:

```text
RADIO#482915#NORMAL#ขอเชิญประชาชนร่วมประชุมหมู่บ้าน
```

ตัวอย่าง Emergency:

```text
RADIO#482915#HIGH#แจ้งเตือนระดับน้ำในคลองเพิ่มสูงขึ้น
```

## Validation Process

1. ตรวจสอบหมายเลขผู้ส่ง
2. ตรวจสอบสถานะ Active ของหมายเลข
3. ตรวจสอบรูปแบบคำสั่ง
4. ตรวจสอบ PIN หรือ Shared Secret
5. ตรวจสอบความยาวข้อความ
6. ตรวจสอบข้อความซ้ำ
7. ตรวจสอบ Rate Limit
8. ตรวจสอบ Priority
9. บันทึกลง SQLite
10. ส่งเข้าคิวประกาศ

## Security Rules

- PIN/Secret ต้องไม่ถูกเก็บเป็น Plain Text
- ห้าม Log PIN หรือ Secret
- ใช้ Hash และ Constant-Time Comparison
- จำกัดจำนวน SMS ต่อหมายเลขต่อช่วงเวลา
- ป้องกัน Replay และ Duplicate Message
- รองรับการ Disable หมายเลขทันที
- บันทึกประวัติการประกาศ
- ห้ามประกาศ OTP หรือข้อมูลส่วนตัว
- ห้ามประกาศ SMS ที่ไม่ผ่าน Command Validation

การตรวจสอบเบอร์ผู้ส่งเพียงอย่างเดียวไม่ถือเป็นการยืนยันตัวตนที่สมบูรณ์ เพราะ Caller ID และ Sender ID อาจถูกปลอมแปลงได้ในบางเส้นทาง

สำหรับข้อความแจ้งเหตุฉุกเฉิน ควรมี Emergency Sender ที่กำหนดชัดเจน และมีมาตรการป้องกันเพิ่มเติม

---

# 9. Phone Call Gateway

ระบบต้องรองรับการรับคำสั่งจากโทรศัพท์ผ่าน SIM7600

## Expected Workflow

```text
Authorized Phone
      |
      | Incoming Call
      v
SIM7600
      |
      | Caller ID Detection
      v
Whitelist Validation
      |
      +---- Unauthorized
      |          |
      |       Reject Call
      |
      +---- Authorized
                 |
           Call Command
                 |
           Trigger Announcement
                 |
             Piper TTS
                 |
           Speaker Playback
```

## Functional Requirements

1. ตรวจสอบ Incoming Call Event
2. อ่านหมายเลขโทรศัพท์จาก Caller ID
3. ตรวจสอบหมายเลขกับ Call Whitelist
4. หากไม่อนุญาต ให้ปฏิเสธสาย
5. หากอนุญาต ให้ทำงานตาม Call Command ที่ลงทะเบียนไว้
6. ปฏิเสธหรือวางสายหลังตรวจสอบ
7. บันทึกประวัติการโทร
8. ป้องกันการเรียกคำสั่งซ้ำ
9. จำกัดจำนวนครั้งในการสั่งงาน
10. ต้องไม่รับสายหรือเปิดไมโครโฟนโดยไม่จำเป็น

## Call Command Design

การโทรเข้าไม่สามารถส่งข้อความประกาศใหม่ได้ด้วยตัวมันเอง

ให้เริ่มจากการกำหนดคำสั่งสำเร็จรูป เช่น:

| Command | Action |
|---|---|
| CALL_001 | ประกาศข้อความประชาสัมพันธ์ประจำวัน |
| CALL_002 | ประกาศข้อความที่ผู้ดูแลกำหนด |
| CALL_003 | แจ้งสถานะระบบ |

หากต้องการให้ผู้โทรพูดข้อความแล้วแปลงเป็นเสียง ต้องพัฒนา Voice IVR และ Speech-to-Text เพิ่มเติมในอนาคต ไม่ถือว่าเป็นความสามารถของระบบ Call Trigger ปัจจุบัน

ตรวจสอบ AT Command และ Call Event ที่รองรับตาม Firmware ของ SIM7600 รุ่นจริงก่อนพัฒนา

---

# 10. Announcement Engine

ระบบใช้ Automatic Announcement

เมื่อ SMS ผ่านการตรวจสอบแล้ว ให้สร้าง Announcement และส่งเข้าคิวทันที

## Announcement Workflow

```text
SMS Received
     |
Validate Sender
     |
Validate Command
     |
Validate Message
     |
Save SQLite
     |
Create Announcement
     |
Announcement Queue
     |
Piper TTS
     |
Generate WAV
     |
Audio Playback
     |
Update Status
```

## Announcement Status

กำหนดสถานะ:

- received
- validated
- queued
- generating
- ready
- playing
- played
- failed
- cancelled

ต้องรองรับ Priority:

- NORMAL
- HIGH
- EMERGENCY

กำหนดนโยบาย Priority ให้ชัดเจน และไม่ให้ข้อความปกติแทรกเสียงประกาศที่กำลังเล่นอยู่

ระบบต้องไม่เล่นเสียงซ้อนกัน

ต้องมีวิธีหยุดเสียงและยกเลิกประกาศจาก Dashboard

---

# 11. Piper Offline TTS

ใช้ Piper TTS เพื่อแปลงข้อความไทยเป็นเสียง

## Requirements

1. รองรับภาษาไทย
2. ทำงาน Offline
3. กำหนดโมเดลเสียงผ่าน Configuration
4. รองรับ Voice Model ชาย/หญิง หากมีโมเดลที่เข้ากัน
5. สร้างไฟล์ WAV
6. ตรวจสอบไฟล์เสียงก่อนส่งเข้า Playback Queue
7. จัดการข้อความยาว
8. จัดการ TTS Error
9. บันทึก Path และ Metadata ของไฟล์เสียง
10. สามารถเปลี่ยน Voice Model ได้โดยไม่แก้ Business Logic

ตัวอย่าง:

```bash
echo "ขอเชิญประชาชนร่วมประชุมหมู่บ้าน" \
| piper \
  --model models_voice/th_TH-model.onnx \
  --output_file static/audio/announcement.wav
```

ตัวอย่าง Playback:

```bash
aplay static/audio/announcement.wav
```

หมายเหตุ:
- ตรวจสอบชื่อไฟล์และตำแหน่งโมเดลจริง
- ต้องตรวจสอบ Architecture ของ Raspberry Pi และความเข้ากันได้ของ Piper
- ต้องตรวจสอบ License ของ Engine และ Voice Model
- ห้ามสมมติว่ามีโมเดลภาษาไทยติดตั้งไว้แล้ว
- ต้องมี Fallback เมื่อ TTS ใช้งานไม่ได้

---

# 12. Speaker Playback

พัฒนา Audio Player สำหรับ Raspberry Pi

## Requirements

- รองรับ ALSA
- รองรับ `aplay`
- ตรวจสอบ Audio Device
- ตรวจสอบไฟล์ WAV
- เล่นเสียงทีละรายการ
- รองรับ Playback Queue
- รองรับ Stop / Pause ตามความสามารถของ Player
- รองรับ Volume Configuration
- ตรวจสอบ Playback Error
- บันทึกสถานะการเล่น
- ป้องกันเสียงเล่นซ้อนกัน

ตัวอย่าง:

```bash
aplay -l
```

ทดสอบเสียง:

```bash
speaker-test -t wav -c 2
```

การเชื่อมต่อลำโพงชุมชนต้องผ่าน Audio Amplifier ที่เหมาะสม ห้ามต่อ Passive Speaker เข้ากับ Audio Output ของ Raspberry Pi โดยตรง

---

# 13. Database Design

ใช้ SQLite เป็นฐานข้อมูลหลัก

แนะนำให้สร้างตาราง:

## sms_messages

- id
- sender
- message
- encoding
- received_at
- modem_index
- processing_status
- raw_pdu
- duplicate_key

## authorized_senders

- id
- phone_number
- display_name
- pin_hash
- is_active
- can_sms
- can_call
- created_at
- updated_at

## announcements

- id
- public_id
- source_type
- source_id
- message
- priority
- status
- audio_path
- created_at
- played_at
- error_message

## announcement_queue

- id
- announcement_id
- priority
- queue_status
- retry_count
- created_at
- started_at
- completed_at

## call_logs

- id
- phone_number
- call_status
- command_id
- received_at
- processed_at

## call_commands

- id
- command_code
- title
- announcement_text
- is_active
- created_at
- updated_at

## system_logs

- id
- level
- module
- message
- created_at

เพิ่ม Index ให้กับคอลัมน์ที่ใช้ค้นหาบ่อย

ใช้ Transaction สำหรับการเปลี่ยนสถานะและการบันทึกข้อมูลที่เกี่ยวข้อง

---

# 14. Flask API

พัฒนา REST API ภายใต้ Prefix:

`/api/v1`

## Health

```http
GET /api/v1/health
```

## SMS

```http
GET /api/v1/sms
GET /api/v1/sms/{id}
```

## Announcements

```http
GET /api/v1/announcements
GET /api/v1/announcements/{id}
POST /api/v1/announcements
POST /api/v1/announcements/{id}/play
POST /api/v1/announcements/{id}/stop
POST /api/v1/announcements/{id}/cancel
```

## Senders

```http
GET /api/v1/senders
POST /api/v1/senders
PUT /api/v1/senders/{id}
DELETE /api/v1/senders/{id}
```

## Calls

```http
GET /api/v1/calls
GET /api/v1/call-commands
POST /api/v1/call-commands
```

## Audio

```http
GET /api/v1/audio/devices
GET /api/v1/audio/status
POST /api/v1/audio/test
```

API ทุก Endpoint ที่เปลี่ยนแปลงข้อมูลต้องตรวจสอบ Authentication และ Authorization

ต้อง Validate Input และกำหนด HTTP Status Code ให้เหมาะสม

---

# 15. Dashboard UX/UI

ออกแบบ Dashboard ให้ใช้งานง่ายบน Desktop, Tablet และ Mobile

ใช้ Bootstrap 5 หรือ Frontend ที่มีอยู่เดิม โดยไม่เปลี่ยน Stack โดยไม่มีเหตุผล

## Dashboard Pages

### 15.1 Overview

แสดง:

- Modem Connection
- SIM Status
- Signal Strength
- Network Registration
- SMS Received Today
- Announcement Count
- Queue Status
- Audio Device Status
- Piper TTS Status
- Last Announcement

### 15.2 SMS Inbox

- รายการ SMS
- หมายเลขผู้ส่ง
- ข้อความ
- เวลา
- Encoding
- Processing Status
- Validation Result

### 15.3 Announcements

- ข้อความประกาศ
- Priority
- สถานะ
- Audio Preview
- Play
- Stop
- Cancel
- Retry

### 15.4 Sender Management

- เพิ่มหมายเลข
- แก้ไขหมายเลข
- Disable / Enable
- กำหนดสิทธิ์ SMS
- กำหนดสิทธิ์ Call
- เปลี่ยน PIN

### 15.5 Call Management

- ประวัติการโทร
- หมายเลขผู้โทร
- สถานะการตรวจสอบ
- Call Command
- เวลาที่โทรเข้า

### 15.6 System Settings

- Serial Port
- Baud Rate
- Piper Model
- Audio Device
- Volume
- Maximum Message Length
- Rate Limit
- Auto Announcement
- System Status

---

# 16. Offline-First Requirements

ระบบหลักต้องทำงานได้โดยไม่ต้องเชื่อมต่อ Internet

รายการที่ต้องใช้งานได้ Offline:

- Flask Dashboard
- SQLite
- SIM7600 SMS Reader
- Call Gateway
- Sender Validation
- PDU Decoder
- Piper TTS
- Audio Playback
- Announcement Queue
- Local Logs

สิ่งที่อาจต้องใช้อินเทอร์เน็ตเฉพาะช่วงติดตั้ง:

- ติดตั้ง Python Packages
- ดาวน์โหลด Piper Engine
- ดาวน์โหลด Voice Model
- อัปเดตระบบปฏิบัติการ

หลังติดตั้งและเตรียมไฟล์ครบแล้ว ระบบต้องไม่เรียก Cloud API หรือ Online TTS ใน Workflow ปกติ

---

# 17. Deployment on Raspberry Pi

รองรับ Raspberry Pi OS 64-bit

เตรียม Environment:

```bash
sudo apt update

sudo apt install -y \
  python3 \
  python3-venv \
  python3-pip \
  sqlite3 \
  alsa-utils \
  git
```

สร้าง Virtual Environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

ตั้งค่า Serial Permission:

```bash
sudo usermod -aG dialout $USER
```

ออกจากระบบแล้ว Login ใหม่เพื่อให้ Group Permission มีผล

ทดสอบ Serial Port:

```bash
ls -l /dev/ttyUSB*
```

ทดสอบ Audio:

```bash
aplay -l
```

## Systemd Services

ต้องสร้าง Service แยกตามหน้าที่:

1. `community-radio.service`
   - Flask Dashboard และ API

2. `community-radio-worker.service`
   - SMS Reader
   - Call Monitor
   - Announcement Worker
   - TTS Worker
   - Audio Playback Worker

ต้องกำหนด Restart Policy และ Logging ให้เหมาะสม

ห้ามให้ Worker หลายตัวเปิด Serial Port เดียวกันโดยไม่ผ่าน AT Command Manager

---

# 18. Reliability and Error Handling

ต้องพัฒนาระบบให้ทนต่อปัญหา:

- SIM ไม่มีสัญญาณ
- SIM ยังไม่พร้อม
- Serial Port หลุด
- Modem Reboot
- SQLite Locked
- Piper ไม่ทำงาน
- Voice Model ไม่พบ
- Audio Device หาย
- WAV เสีย
- Queue ค้าง
- Raspberry Pi Restart ระหว่างประกาศ
- SMS ซ้ำ
- Multipart SMS มาไม่ครบ

ทุก Error ต้องมี Log และมีแนวทาง Recovery

หลัง Raspberry Pi Restart ต้องสามารถอ่านสถานะงานค้างจาก SQLite และจัดการได้โดยไม่ประกาศข้อความซ้ำโดยไม่ตั้งใจ

---

# 19. Testing Strategy

ต้องมี Unit Test และ Integration Test

## Unit Tests

- PDU Decoder
- UCS2 Decoder
- GSM-7 Decoder
- Multipart SMS Reassembly
- Sender Whitelist
- PIN Validation
- Duplicate Detection
- Command Parser
- Announcement Processor
- Priority Queue
- Call Number Validation

## Integration Tests

- Flask + SQLite
- SIM7600 Mock Serial
- Piper Mock
- Audio Player Mock
- Queue + TTS
- Queue + Audio Playback

## Hardware Tests

ทดสอบบน Raspberry Pi จริง:

1. SIM7600 Detect
2. SIM Ready
3. Network Registration
4. รับ SMS ภาษาอังกฤษ
5. รับ SMS ภาษาไทย
6. รับ Multipart SMS
7. ตรวจสอบ Whitelist
8. ประกาศอัตโนมัติ
9. รับสายจากหมายเลขที่อนุญาต
10. ปฏิเสธสายที่ไม่อนุญาต
11. Piper สร้างเสียงภาษาไทย
12. เล่นเสียงผ่าน Amplifier
13. Restart แล้วระบบกลับมาทำงาน
14. ทดสอบโดยถอด WAN Internet

ห้ามรายงานว่า Hardware Test ผ่าน หากยังไม่ได้ทดสอบกับอุปกรณ์จริง

---

# 20. Development Roadmap

ให้พัฒนาตามลำดับนี้

## Phase 1: Source Code Audit

- ตรวจสอบ Project เดิม
- ตรวจสอบไฟล์ทั้งหมด
- ตรวจสอบ Flask Routes
- ตรวจสอบ SQLite Models
- ตรวจสอบ API เดิม
- ตรวจสอบ Dependencies
- ตรวจสอบ Configuration
- สร้าง Technical Audit Report

Deliverable:

`docs/technical-audit.md`

## Phase 2: SIM7600 SMS Gateway

- Serial Manager
- AT Command Manager
- SIM Status
- Signal Status
- Network Status
- SMS Reader
- SMS Storage

Deliverable:

รับ SMS และบันทึก SQLite ได้

## Phase 3: Thai PDU Decoder

- GSM-7
- UCS2
- UDH
- Multipart SMS
- Duplicate Detection

Deliverable:

รับและถอดรหัสข้อความภาษาไทยได้ถูกต้อง

## Phase 4: Sender Whitelist

- Sender CRUD
- PIN Hash
- Command Parser
- Authorization
- Rate Limit

Deliverable:

ประกาศเฉพาะ SMS ที่ได้รับอนุญาต

## Phase 5: Piper Offline TTS

- Piper Integration
- Voice Model Configuration
- WAV Generation
- Error Handling

Deliverable:

สร้างเสียงภาษาไทยแบบ Offline ได้

## Phase 6: Speaker Playback

- Audio Device Detection
- ALSA Integration
- Playback Queue
- Stop / Retry
- Playback Logs

Deliverable:

เล่นเสียงผ่านลำโพงได้จริง

## Phase 7: Phone Call Gateway

- Incoming Call Detection
- Caller ID
- Call Whitelist
- Call Command
- Call Logs

Deliverable:

โทรศัพท์ที่ได้รับอนุญาตสามารถสั่งประกาศข้อความสำเร็จรูปได้

## Phase 8: Dashboard

- Overview
- SMS Inbox
- Announcement Management
- Sender Management
- Call Management
- System Settings

Deliverable:

จัดการระบบผ่าน LAN และ Localhost ได้

## Phase 9: Production Deployment

- Systemd
- Auto Restart
- Log Rotation
- Database Backup
- Offline Test
- Hardware Integration Test

Deliverable:

ระบบพร้อมติดตั้งและทดลองใช้งานในพื้นที่จริง

---

# 21. Security and Operational Safety

เนื่องจากระบบสามารถกระจายเสียงไปยังประชาชนจำนวนมาก ต้องให้ความสำคัญกับความปลอดภัย

1. ไม่ประกาศข้อความจากเบอร์ที่ไม่อนุญาต
2. ไม่ประกาศข้อความที่ไม่มี Command Format ถูกต้อง
3. จำกัดความยาวข้อความ
4. ป้องกัน Spam
5. ป้องกันการประกาศซ้ำ
6. มี Emergency Sender ที่กำหนดสิทธิ์ชัดเจน
7. บันทึกประวัติการประกาศทุกครั้ง
8. มีปุ่ม Stop Announcement
9. มี Admin Authentication
10. ห้ามเปิด Dashboard สู่ Public Internet โดยไม่มีระบบรักษาความปลอดภัยที่เหมาะสม
11. ไม่บันทึก PIN, Password หรือ API Key ลง Log
12. ไม่ประกาศข้อมูลส่วนบุคคลหรือข้อมูลลับโดยอัตโนมัติ

สำหรับระบบประกาศสาธารณะ ต้องตรวจสอบความเหมาะสมของข้อความและสิทธิ์การใช้งาน รวมถึงข้อกำหนดด้านกิจการวิทยุกระจายเสียงที่เกี่ยวข้องก่อนนำไปใช้งานจริง

---

# 22. Environment Variables

ตัวอย่าง `.env.example`

```dotenv
APP_ENV=production
APP_HOST=0.0.0.0
APP_PORT=5000
SECRET_KEY=change-this-secret

DATABASE_URL=sqlite:///instance/community_radio.db

ADMIN_USERNAME=admin
ADMIN_PASSWORD=change-this-password
RADIO_API_KEY=change-this-api-key

SMS_ENABLED=true
SMS_PORT=/dev/ttyUSB2
SMS_BAUD=115200

SMS_AUTO_DELETE=true
SMS_POLL_INTERVAL=3

CALL_ENABLED=true
CALL_AUTO_REJECT=true

AUTO_ANNOUNCE=true

PIPER_EXECUTABLE=piper
PIPER_MODEL=models_voice/th_TH-model.onnx

AUDIO_PLAYER=aplay
AUDIO_DEVICE=default

MAX_MESSAGE_LENGTH=500
RATE_LIMIT_PER_HOUR=10

LOG_LEVEL=INFO
```

ค่าทั้งหมดเป็นตัวอย่าง ต้องตรวจสอบให้ตรงกับอุปกรณ์และ Environment จริง

---

# 23. Acceptance Criteria

ระบบจะถือว่าผ่าน MVP เมื่อ:

- [ ] Flask ทำงานได้บน Raspberry Pi
- [ ] SQLite บันทึกข้อมูลได้
- [ ] Dashboard เข้าใช้งานผ่าน Localhost ได้
- [ ] Dashboard เข้าใช้งานผ่าน LAN ได้
- [ ] SIM7600 เชื่อมต่อได้จริง
- [ ] อ่าน SMS ได้จริง
- [ ] Decode SMS ภาษาไทยได้
- [ ] รองรับ Multipart SMS
- [ ] Sender Whitelist ทำงานได้
- [ ] ตรวจสอบ PIN/Secret ได้
- [ ] SMS ที่ผ่าน Validation ถูกส่งเข้าคิวอัตโนมัติ
- [ ] Piper สร้างเสียงภาษาไทยแบบ Offline ได้
- [ ] Audio Player เล่นเสียงได้จริง
- [ ] Call Gateway ตรวจสอบเบอร์โทรได้จริง
- [ ] Call Command ทำงานได้
- [ ] ไม่มีเสียงเล่นซ้อนกัน
- [ ] มี Error Logging
- [ ] ระบบกลับมาทำงานหลัง Restart
- [ ] ทดสอบระบบโดยไม่มี WAN Internet แล้วผ่าน

แยกสถานะผลทดสอบเป็น:

- PASS: ทดสอบแล้วผ่าน
- FAIL: ทดสอบแล้วไม่ผ่าน
- NOT TESTED: ยังไม่ได้ทดสอบ
- BLOCKED: ติดข้อจำกัดที่ต้องแก้ไขก่อน

---

# 24. Instructions for Claude Code

เมื่อเริ่มทำงานใน Repository ให้ปฏิบัติตามลำดับ:

**Step 1 — Inspect**

ตรวจสอบ Source Code เดิมทั้งหมดก่อน ห้ามเริ่มเขียนโค้ดทันที

**Step 2 — Audit**

สร้าง `docs/technical-audit.md` ระบุสิ่งที่มีอยู่แล้ว สิ่งที่ขาด และสิ่งที่ต้องแก้ไข

**Step 3 — Plan**

สร้าง `docs/development-plan.md` ระบุไฟล์ที่ต้องเพิ่ม/แก้ไข พร้อมลำดับงาน

**Step 4 — Implement**

เริ่มพัฒนาทีละ Phase โดยรักษาความเข้ากันได้กับ API และ Database เดิมให้มากที่สุด

**Step 5 — Test**

รัน Unit Tests และ Integration Tests หลังแก้ไขทุกส่วน

**Step 6 — Document**

อัปเดต README, Installation Guide, Hardware Setup และ Troubleshooting

**Step 7 — Report**

สรุป:
- สิ่งที่พัฒนาเสร็จ
- ไฟล์ที่เพิ่ม
- ไฟล์ที่แก้ไข
- คำสั่งติดตั้ง
- คำสั่งรัน
- ผลการทดสอบ
- ปัญหาที่ยังเหลือ
- ขั้นตอนถัดไป

## First Task

เริ่มต้นด้วยการตรวจสอบ Repository ปัจจุบันของ Community Radio SMS Gateway Offline Edition

ห้ามเขียนระบบใหม่ทั้งหมด

ให้ตรวจสอบว่า Demo เดิมมี Flask, SQLite, Dashboard, Webhook และ Announcement API อะไรอยู่แล้ว จากนั้นออกแบบการต่อยอด SIM7600, Thai PDU Decoder, Sender Whitelist, Piper Offline TTS, Speaker Playback และ Phone Call Gateway ให้ทำงานร่วมกับระบบเดิม

เริ่มจาก Phase 1 และรายงานผล Audit ก่อนลงมือแก้ไข Source Code

**เป้าหมายสุดท้าย:** Community Radio SMS Gateway ที่ทำงานบน Raspberry Pi ได้ตลอด 24 ชั่วโมง รับ SMS และคำสั่งโทรศัพท์โดยไม่พึ่ง WAN Internet แปลงข้อความภาษาไทยเป็นเสียง และประกาศผ่านลำโพงชุมชนได้อย่างปลอดภัยและตรวจสอบย้อนหลังได้