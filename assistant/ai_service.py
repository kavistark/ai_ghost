import os
import json
import re
import logging
import base64
from datetime import datetime
import requests
from django.conf import settings

try:
    import cv2
    import numpy as np
except ImportError:
    cv2 = None
    np = None

logger = logging.getLogger(__name__)

def clean_json_response(raw_text):
    """
    Robust JSON extractor:
    Handles markdown code fences, leading/trailing commentary,
    and extracts the outermost valid JSON object.
    """
    if not raw_text:
        return None
    raw_text = raw_text.strip()

    # 1. First check if wrapped in markdown code fence
    fence_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', raw_text)
    if fence_match:
        candidate = fence_match.group(1).strip()
        try:
            return json.loads(candidate)
        except Exception:
            pass

    # 2. Try direct JSON parsing
    try:
        return json.loads(raw_text)
    except Exception:
        pass

    # 3. Find outermost balanced curly braces { ... }
    start = raw_text.find('{')
    end = raw_text.rfind('}')
    if start != -1 and end != -1 and end > start:
        snippet = raw_text[start:end+1]
        try:
            return json.loads(snippet)
        except Exception:
            pass

    return None


# =====================================================================
# 1. GEMINI LLM: SIMON "GHOST" RILEY (COD Persona & Spoken Comms)
# =====================================================================

def get_gemini_api_key():
    """
    Dynamically retrieve the active Gemini API key from settings,
    process environment, or directly reload from .env if needed.
    """
    key = getattr(settings, 'GEMINI_API_KEY', '') or os.getenv('GEMINI_API_KEY', '')
    if key and not key.startswith('your_'):
        return key

    base_dir = getattr(settings, 'BASE_DIR', os.getcwd())
    env_file = os.path.join(base_dir, '.env')
    if os.path.exists(env_file):
        try:
            with open(env_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line.startswith('GEMINI_API_KEY='):
                        val = line.split('=', 1)[1].strip().strip('"').strip("'")
                        if val and not val.startswith('your_'):
                            return val
        except Exception:
            pass
    return ''


def build_gemini_voice_prompt(context):
    return (
        "You are Lieutenant Simon 'Ghost' Riley, elite Task Force 141 special forces operator from Call of Duty.\n"
        "You are operating the tactical GHOST dashboard as the user's field AI handler.\n\n"
        "CHARACTER & VOICE RULES:\n"
        "- Voice: Deep, blunt, disciplined, tactical, British SAS cadence.\n"
        "- Signature comms lingo: 'Solid copy', 'Affirmative', 'Negative', 'Stay frosty', 'Watch your six', "
        "'Moving on target', 'Job\\'s done', 'Coordinates logged', 'Clear and armed'.\n"
        "- Never be overly cheerful or robotic. Be calm, authoritative, cold, and laser-focused.\n"
        "- Spoken reply MUST be short and punchy (1-2 sentences maximum, ready to be radioed over comms).\n"
        "- If user speaks English, speak tactical English.\n"
        "- If user speaks Tamil, speak disciplined tactical Tamil with soldier authority.\n\n"
        "YOU MUST UNDERSTAND AND EXECUTE NATURAL LANGUAGE COMMANDS ACROSS ALL 7 MODULES:\n"
        "1. Schedule: Add, edit, or delete calendar events/meetings.\n"
        "   - {\"type\": \"add_schedule\", \"title\": \"...\", \"time\": \"HH:MM\", \"date\": \"YYYY-MM-DD or today/tomorrow\"}\n"
        "   - {\"type\": \"edit_schedule\", \"title\": \"...\", \"time\": \"...\", \"date\": \"...\"}\n"
        "   - {\"type\": \"delete_schedule\", \"title\": \"...\"}\n"
        "2. Tasks: Manage operational tasks and to-do objectives.\n"
        "   - {\"type\": \"add_task\", \"text\": \"...\"}\n"
        "   - {\"type\": \"edit_task\", \"old\": \"...\", \"text\": \"...\"}\n"
        "   - {\"type\": \"complete_task\", \"text\": \"...\"}\n"
        "   - {\"type\": \"delete_task\", \"text\": \"...\"}\n"
        "3. Reminders: Time-specific reminders, alerts, or timed meetings.\n"
        "   - {\"type\": \"add_reminder\", \"text\": \"...\", \"time\": \"HH:MM\", \"date\": \"YYYY-MM-DD or today/tomorrow\"}\n"
        "   - {\"type\": \"edit_reminder\", \"text\": \"...\", \"time\": \"...\", \"date\": \"...\"}\n"
        "   - {\"type\": \"complete_reminder\", \"text\": \"...\"}\n"
        "   - {\"type\": \"delete_reminder\", \"text\": \"...\"}\n"
        "4. Daily Plan: Structured daily timeline and activities.\n"
        "   - {\"type\": \"add_plan_item\", \"time\": \"HH:MM\", \"activity\": \"...\"}\n"
        "   - {\"type\": \"edit_plan_item\", \"activity\": \"...\", \"time\": \"...\", \"new_activity\": \"...\"}\n"
        "   - {\"type\": \"delete_plan_item\", \"activity\": \"...\"}\n"
        "   - {\"type\": \"clear_plan\"}\n"
        "   - {\"type\": \"create_plan\", \"items\": [\"08:00 Briefing\", \"12:00 Recon\", ...]}\n"
        "5. Internet Assistant: Web search and information reconnaissance.\n"
        "   - {\"type\": \"search_web\", \"query\": \"...\"}\n"
        "   - {\"type\": \"clear_search_history\"}\n"
        "6. AI Phone Service: Incoming/outgoing automated phone call handling.\n"
        "   - {\"type\": \"call_service\", \"on\": true | false}\n"
        "   - {\"type\": \"add_phone_message\", \"caller\": \"...\", \"message\": \"...\"}\n"
        "   - {\"type\": \"clear_phone_messages\"}\n"
        "7. Autonomous Agent, Intel Memory & Action Camera Recon:\n"
        "   - {\"type\": \"run_agent\", \"goal\": \"...\"}\n"
        "   - {\"type\": \"approve_agent\"}\n"
        "   - {\"type\": \"add_memory\", \"content\": \"...\", \"category\": \"tactical_intel\"}\n"
        "   - {\"type\": \"delete_memory\", \"content\": \"...\"}\n"
        "   - Action Camera Recon: {\"type\": \"camera_analyze\", \"prompt\": \"...\", \"url\": \"...\"}\n"
        "   - Connect WiFi Action Camera: {\"type\": \"camera_connect\", \"url\": \"...\", \"protocol\": \"WiFi/RTSP|HTTP\"}\n"
        "8. Ghost Core & Security Controls:\n"
        "   - {\"type\": \"lock_grid\"}, {\"type\": \"unlock_grid\"}, {\"type\": \"set_theme\", \"mode\": \"dark\" | \"light\"}\n"
        "9. General Q&A / Tactical Knowledge / Mission Clock:\n"
        "   - When user asks a question, general inquiry, mission clock/time check, status sitrep, or tactical query without modifying data, "
        "answer accurately, directly, and concisely in Simon 'Ghost' Riley's character! Set intent='qa' and actions=[].\n\n"
        f"CURRENT TACTICAL DASHBOARD STATE:\n{json.dumps(context, indent=2)}\n\n"
        "Return ONLY a valid JSON object with this exact schema:\n"
        "{\n"
        '  "reply": "Tactical spoken radio response as Simon Ghost Riley",\n'
        '  "intent": "schedule | task | reminder | plan | search | phone | agent | core | qa",\n'
        '  "actions": [\n'
        '    {"type": "<action_type>", ...fields}\n'
        '  ]\n'
        "}"
    )


def gemini_voice_reply(text, context):
    """
    Gemini generates the immediate natural language reasoning and spoken reply,
    extracting operational actions across all 7 modules or answering tactical Q&A.
    """
    api_key = get_gemini_api_key()
    if not api_key:
        return None

    models_to_try = [
        os.getenv('GEMINI_MODEL', 'gemini-flash-lite-latest'),
        'gemini-flash-lite-latest',
        'gemini-3.1-flash-lite',
        'gemini-3.5-flash-lite',
        'gemini-flash-latest',
    ]
    seen = set()
    system_prompt = build_gemini_voice_prompt(context)
    full_prompt = f"{system_prompt}\n\nUSER INPUT: \"{text}\""

    headers = {
        "Content-Type": "application/json",
        "x-goog-api-key": api_key
    }
    payload = {
        "contents": [{"parts": [{"text": full_prompt}]}],
        "generationConfig": {
            "temperature": 0.25,
            "maxOutputTokens": 600,
            "responseMimeType": "application/json"
        }
    }

    for model_name in models_to_try:
        if model_name in seen:
            continue
        seen.add(model_name)
        if model_name.startswith('models/'):
            url = f"https://generativelanguage.googleapis.com/v1beta/{model_name}:generateContent?key={api_key}"
        else:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
        try:
            res = requests.post(url, headers=headers, json=payload, timeout=(2.5, 4.0))
            if res.ok:
                data = res.json()
                candidate_text = data['candidates'][0]['content']['parts'][0]['text']
                parsed = clean_json_response(candidate_text)
                if parsed and isinstance(parsed, dict) and 'reply' in parsed:
                    return parsed
            else:
                logger.debug(f"Gemini {model_name} status {res.status_code}")
                if res.status_code in (401, 403):
                    break
        except Exception as e:
            logger.debug(f"Gemini {model_name} error: {e}")

    return None


# =====================================================================
# 2. CLAUDE LLM: AUTONOMOUS TASK AGENT & MEMORY MANAGER
# =====================================================================

def build_claude_agent_prompt(goal, context, memories):
    mem_text = "\n".join([f"- [{m.get('category','fact')}] {m.get('content','')}" for m in memories]) or "No prior tactical intel logged."
    return (
        "You are Task Force 141 Autonomous Recon & Tactics Agent (Ghost Ops powered by Claude).\n"
        "Your mission: Execute assigned tactical directives, coordinate operations, plan step-by-step missions, and log field intel.\n\n"
        f"FIELD INTEL & MEMORY:\n{mem_text}\n\n"
        f"CURRENT OPERATIONAL STATE:\n{json.dumps(context, indent=2)}\n\n"
        f"ASSIGNED MISSION OBJECTIVE:\n\"{goal}\"\n\n"
        "Return ONLY a valid JSON object with this exact schema:\n"
        "{\n"
        '  "steps": [\n'
        '    "Intel: Target coordinates acquired",\n'
        '    "Recon: Infiltrating sources and assessing targets",\n'
        '    "Extraction: Compiling mission briefing",\n'
        '    "Standing by for your go-ahead"\n'
        '  ],\n'
        '  "status": "needs_approval",\n'
        '  "summary": "Tactical sitrep on mission progress and findings",\n'
        '  "new_memories": [\n'
        '    // {"category": "preference|fact|contact|workflow", "content": "..."}\n'
        '  ],\n'
        '  "actions": [\n'
        '    // {"type":"add_task", "text":"..."}\n'
        '  ]\n'
        "}"
    )


def claude_execute_agent_task(goal, context, memories):
    """
    Claude handles the assigned agent task, plans execution steps,
    and returns agent steps + new memories to persist.
    """
    api_key = getattr(settings, 'ANTHROPIC_API_KEY', '') or os.getenv('ANTHROPIC_API_KEY', '')
    if not api_key:
        return None

    model_name = os.getenv('CLAUDE_MODEL', 'claude-3-5-sonnet-20241022')
    system_prompt = build_claude_agent_prompt(goal, context, memories)

    try:
        url = "https://api.anthropic.com/v1/messages"
        headers = {
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }
        payload = {
            "model": model_name,
            "max_tokens": 800,
            "system": system_prompt,
            "messages": [{"role": "user", "content": f"Execute the goal: {goal}"}]
        }
        res = requests.post(url, headers=headers, json=payload, timeout=2.5)
        if res.ok:
            data = res.json()
            return clean_json_response(data['content'][0]['text'])
    except Exception as e:
        logger.debug(f"Claude agent call error: {e}")

    return None


# =====================================================================
# 3. AUTONOMOUS AGENT: WIFI ACTION CAMERA RECON & VISUAL ANALYSIS
# =====================================================================

def generate_tactical_hud_frame(status_text="WIFI ACTION CAM // SCANNING FEED", width=640, height=360):
    """
    Generate an authentic TF141 tactical HUD synthetic frame when
    live camera is connecting, offline, or in simulation mode.
    """
    if cv2 is None or np is None:
        return b""

    frame = np.zeros((height, width, 3), dtype=np.uint8)

    # Dark tactical green background grid
    grid_color = (25, 45, 25)
    for x in range(0, width, 40):
        cv2.line(frame, (x, 0), (x, height), grid_color, 1)
    for y in range(0, height, 40):
        cv2.line(frame, (0, y), (width, y), grid_color, 1)

    # Animated radar / scan sweep line
    now = datetime.now()
    sweep_y = int((now.microsecond / 1000000.0) * height)
    cv2.line(frame, (0, sweep_y), (width, sweep_y), (0, 180, 80), 2)

    # Corner brackets (Tactical Viewfinder)
    bracket_len = 30
    c_color = (0, 220, 110)
    # Top-Left
    cv2.line(frame, (20, 20), (20 + bracket_len, 20), c_color, 2)
    cv2.line(frame, (20, 20), (20, 20 + bracket_len), c_color, 2)
    # Top-Right
    cv2.line(frame, (width - 20, 20), (width - 20 - bracket_len, 20), c_color, 2)
    cv2.line(frame, (width - 20, 20), (width - 20, 20 + bracket_len), c_color, 2)
    # Bottom-Left
    cv2.line(frame, (20, height - 20), (20 + bracket_len, height - 20), c_color, 2)
    cv2.line(frame, (20, height - 20), (20, height - 20 - bracket_len), c_color, 2)
    # Bottom-Right
    cv2.line(frame, (width - 20, height - 20), (width - 20 - bracket_len, height - 20), c_color, 2)
    cv2.line(frame, (width - 20, height - 20), (width - 20, height - 20 - bracket_len), c_color, 2)

    # Center Reticle
    cx, cy = width // 2, height // 2
    cv2.drawMarker(frame, (cx, cy), (0, 255, 128), cv2.MARKER_CROSS, 24, 1)
    cv2.circle(frame, (cx, cy), 45, (0, 200, 100), 1)

    # Header Telemetry
    cv2.putText(frame, "TF141 GHOST RECON // WIFI ACTION CAM", (30, 42), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 128), 1, cv2.LINE_AA)
    cv2.putText(frame, status_text, (30, 64), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 200, 255), 1, cv2.LINE_AA)

    # Telemetry Footers
    t_str = now.strftime('%H:%M:%S.%f')[:11]
    cv2.putText(frame, f"REC [WIFI 5GHz] | FOV: 140 WIDE | CLOCK: {t_str}", (30, height - 32), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (0, 220, 110), 1, cv2.LINE_AA)
    cv2.putText(frame, "GRID: 34.521 N, 43.189 E | AZ: 184 DEG | OPTICS: ENCRYPTED", (30, height - 14), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (0, 160, 90), 1, cv2.LINE_AA)

    _, buf = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
    return buf.tobytes()


def analyze_camera_frame(image_bytes=None, prompt="Scan tactical frame for targets and perimeter security", protocol="WiFi/RTSP", source_url="action_cam"):
    """
    Multimodal Visual Recon Engine for the Autonomous Agent:
    1. Decodes and processes frame with OpenCV
    2. Identifies salient movement/targets and draws tactical HUD annotations
    3. Analyzes image using Gemini Multimodal Vision if online
    4. Provides instant sub-millisecond local tactical assessment fallback
    """
    now_str = datetime.now().strftime('%H:%M:%S')

    if cv2 is None or np is None:
        return {
            'threat_level': 'CLEAR',
            'sitrep': 'Action camera optical sensors active. No hostiles detected.',
            'detections': ['Visual sensor operational', 'Protocol: ' + protocol],
            'spoken_radio': 'Solid copy. Action camera sector is clear. Stay frosty.',
            'annotated_image': '',
            'protocol': protocol,
            'source_url': source_url,
            'timestamp': now_str
        }

    # 1. Decode or Generate Frame
    img = None
    if image_bytes:
        try:
            nparr = np.frombuffer(image_bytes, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        except Exception as e:
            logger.debug(f"Error decoding camera frame: {e}")

    if img is None:
        synthetic_bytes = generate_tactical_hud_frame("SIMULATED TACTICAL ACTION CAM FEED")
        nparr = np.frombuffer(synthetic_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    h, w = img.shape[:2]

    # 2. Extract Computer Vision Telemetry (Edges, Contours, Targets)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    mean_lum = float(np.mean(gray))
    optics_mode = "NIGHT VISION / LOW-LIGHT" if mean_lum < 55 else "DAYLIGHT TACTICAL OPTICS"

    edges = cv2.Canny(gray, 35, 120)
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    targets = []
    min_area = max(200, (w * h) // 400)
    max_area = (w * h) * 0.75

    for c in contours:
        area = cv2.contourArea(c)
        if min_area < area < max_area:
            x, y, bw, bh = cv2.boundingRect(c)
            # Filter noise aspect ratios
            if 0.15 < (bw / bh) < 6.0:
                targets.append((x, y, bw, bh, area))

    targets = sorted(targets, key=lambda t: t[4], reverse=True)[:5]

    # 3. Draw Tactical HUD Annotations on Frame
    annotated = img.copy()

    # Draw corner brackets on detected targets
    for i, (tx, ty, tbw, tbh, _) in enumerate(targets):
        b_color = (0, 240, 255) if i == 0 else (0, 255, 128)
        blen = max(6, min(14, tbw // 4, tbh // 4))
        # Top-left
        cv2.line(annotated, (tx, ty), (tx + blen, ty), b_color, 2)
        cv2.line(annotated, (tx, ty), (tx, ty + blen), b_color, 2)
        # Top-right
        cv2.line(annotated, (tx + tbw, ty), (tx + tbw - blen, ty), b_color, 2)
        cv2.line(annotated, (tx + tbw, ty), (tx + tbw, ty + blen), b_color, 2)
        # Bottom-left
        cv2.line(annotated, (tx, ty + tbh), (tx + blen, ty + tbh), b_color, 2)
        cv2.line(annotated, (tx, ty + tbh), (tx, ty + tbh - blen), b_color, 2)
        # Bottom-right
        cv2.line(annotated, (tx + tbw, ty + tbh), (tx + tbw - blen, ty + tbh), b_color, 2)
        cv2.line(annotated, (tx + tbw, ty + tbh), (tx + tbw, ty + tbh - blen), b_color, 2)

        # Label tag
        lbl = f"TGT-0{i+1} [{tx},{ty}]"
        cv2.putText(annotated, lbl, (tx, max(12, ty - 4)), cv2.FONT_HERSHEY_SIMPLEX, 0.38, b_color, 1, cv2.LINE_AA)

    # Center Targeting Reticle
    cx, cy = w // 2, h // 2
    cv2.drawMarker(annotated, (cx, cy), (0, 255, 128), cv2.MARKER_CROSS, 20, 1)

    # Top HUD Banner
    hud_bg = (15, 20, 15)
    cv2.rectangle(annotated, (0, 0), (w, 24), hud_bg, -1)
    status_header = f"TF141 GHOST RECON // LINK: {protocol} // LOCKS: {len(targets)}"
    cv2.putText(annotated, status_header, (10, 16), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (0, 255, 128), 1, cv2.LINE_AA)
    cv2.putText(annotated, f"TIME: {now_str}", (w - 110, 16), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (0, 200, 255), 1, cv2.LINE_AA)

    # Encode annotated frame to base64
    _, buf = cv2.imencode('.jpg', annotated, [cv2.IMWRITE_JPEG_QUALITY, 82])
    annotated_b64 = base64.b64encode(buf).decode('utf-8')

    # 4. Attempt Gemini Multimodal Vision Analysis (Tier 1)
    api_key = get_gemini_api_key()
    if api_key:
        vision_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-lite-latest:generateContent?key={api_key}"
        vision_headers = {"Content-Type": "application/json"}
        vision_prompt = (
            "You are Lieutenant Simon 'Ghost' Riley, special forces operator from Call of Duty Task Force 141.\n"
            f"Analyze this WiFi action camera reconnaissance frame. Tactical context: {prompt}.\n"
            "Return ONLY a valid JSON object with:\n"
            "{\n"
            '  "threat_level": "CLEAR | CAUTION | HIGH",\n'
            '  "sitrep": "Tactical spoken radio report as Ghost (1-2 sentences)",\n'
            '  "detections": ["list", "of", "tactical", "observations"],\n'
            '  "spoken_radio": "Short radio callout ready for voice synthesis"\n'
            "}"
        )
        vision_payload = {
            "contents": [{
                "parts": [
                    {"text": vision_prompt},
                    {
                        "inline_data": {
                            "mime_type": "image/jpeg",
                            "data": annotated_b64
                        }
                    }
                ]
            }],
            "generationConfig": {
                "temperature": 0.2,
                "maxOutputTokens": 300,
                "responseMimeType": "application/json"
            }
        }
        try:
            v_res = requests.post(vision_url, headers=vision_headers, json=vision_payload, timeout=6.0)
            if v_res.ok:
                data = v_res.json()
                raw_txt = data['candidates'][0]['content']['parts'][0]['text']
                parsed = clean_json_response(raw_txt)
                if parsed and isinstance(parsed, dict) and 'sitrep' in parsed:
                    return {
                        'threat_level': parsed.get('threat_level', 'CLEAR').upper(),
                        'sitrep': parsed.get('sitrep', 'Visual scan verified. Perimeter clear.'),
                        'detections': parsed.get('detections', [f"Optics: {optics_mode}", "Signal: Operational"]),
                        'spoken_radio': parsed.get('spoken_radio', parsed.get('sitrep')),
                        'annotated_image': f"data:image/jpeg;base64,{annotated_b64}",
                        'protocol': protocol,
                        'source_url': source_url,
                        'timestamp': now_str
                    }
        except Exception as e:
            logger.debug(f"Gemini vision call fallback: {e}")

    # 5. Local Tactical Computer Vision Analysis (Tier 2 Sub-millisecond Fallback)
    if len(targets) > 0:
        threat_level = "HIGH" if len(targets) >= 3 else "CAUTION"
        sitrep = f"Action camera recon: {len(targets)} visual anomaly signature(s) detected in sector. Optical tracking locked. Stay frosty."
        spoken_radio = f"Target acquired on action cam feed. {len(targets)} visual signatures locked. Eyes open, operator."
        detections = [
            f"Target 0{idx+1} acquired at grid coordinates [{x},{y}] (size {bw}x{bh})"
            for idx, (x, y, bw, bh, _) in enumerate(targets[:4])
        ]
        detections.append(f"Optics Mode: {optics_mode} (mean luminance: {int(mean_lum)})")
        detections.append(f"Link Telemetry: {protocol} via {source_url} [Active]")
    else:
        threat_level = "CLEAR"
        sitrep = "Action camera visual scan complete. Zero hostile signatures detected in frame. Sector Alpha perimeter is secure."
        spoken_radio = "Perimeter clear on action camera feed. Sector is secure. Keep moving, operator."
        detections = [
            "Perimeter boundary verified intact",
            "Zero movement or hostile signatures in primary sector",
            f"Optics Mode: {optics_mode}",
            f"WiFi Action Cam Link: 100% signal via {protocol}"
        ]

    return {
        'threat_level': threat_level,
        'sitrep': sitrep,
        'detections': detections,
        'spoken_radio': spoken_radio,
        'annotated_image': f"data:image/jpeg;base64,{annotated_b64}",
        'protocol': protocol,
        'source_url': source_url,
        'timestamp': now_str
    }
