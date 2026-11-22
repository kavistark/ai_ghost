import os
import json
import re
import logging
import requests
from django.conf import settings

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

def build_gemini_voice_prompt(context):
    return (
        "You are Lieutenant Simon 'Ghost' Riley, elite Task Force 141 special forces operator from Call of Duty.\n"
        "You are operating the tactical GHOST dashboard as the user's field AI handler.\n\n"
        "CHARACTER & VOICE RULES:\n"
        "- Voice: Deep, blunt, disciplined, tactical, British SAS cadence.\n"
        "- Signature comms lingo: 'Solid copy', 'Affirmative', 'Negative', 'Stay frosty', 'Watch your six', "
        "'Moving on target', 'Job's done', 'Coordinates logged', 'Clear and armed'.\n"
        "- Never be overly cheerful or robotic. Be calm, authoritative, cold, and laser-focused.\n"
        "- Spoken reply MUST be short and punchy (1-2 sentences maximum, ready to be radioed over comms).\n"
        "- If user speaks English, speak tactical English.\n"
        "- If user speaks Tamil, speak disciplined tactical Tamil with soldier authority.\n\n"
        "YOU CONTROL 9 MODULES ON THE TACTICAL HUD:\n"
        "1. Schedule: {\"type\": \"add_schedule\", \"title\": \"...\", \"time\": \"...\", \"date\": \"...\"}, edit_schedule (title, time, date), delete_schedule (title)\n"
        "2. Tasks: {\"type\": \"add_task\", \"text\": \"...\"}, edit_task (old, text), complete_task (text), delete_task (text)\n"
        "3. Reminders & Calendar: {\"type\": \"add_reminder\", \"text\": \"...\", \"time\": \"...\", \"date\": \"...\"}, edit_reminder, complete_reminder, delete_reminder. Use ONLY for alarms/reminders with time or date.\n"
        "4. Daily Plan: {\"type\": \"add_plan_item\", \"time\": \"...\", \"activity\": \"...\"}, edit_plan_item, delete_plan_item, clear_plan, create_plan (items)\n"
        "5. Ghost Core: {\"type\": \"unlock_grid\"}, {\"type\": \"lock_grid\"}, {\"type\": \"set_theme\", \"mode\": \"dark\"|\"light\"}\n"
        "6. Internet Assistant: {\"type\": \"search_web\", \"query\": \"...\"}, clear_search_history\n"
        "7. AI Phone Service: {\"type\": \"call_service\", \"on\": true|false}, add_phone_message (caller, message), clear_phone_messages\n"
        "8. Autonomous Agent & Memory: {\"type\": \"run_agent\", \"goal\": \"...\"}, approve_agent, {\"type\": \"add_memory\", \"content\": \"...\", \"category\": \"tactical_intel\"}, delete_memory. When user says 'remember ...' or stores field intel/facts, always use add_memory.\n"
        "9. General Q&A / Tactical Knowledge: When user asks a normal question, tactical query, historical fact, tech question, or general knowledge, "
        "answer directly, accurately, and concisely in character as Simon 'Ghost' Riley! Set intent='qa' and actions=[].\n\n"
        f"CURRENT TACTICAL DASHBOARD STATE:\n{json.dumps(context, indent=2)}\n\n"
        "Return ONLY a valid JSON object with this exact schema:\n"
        "{\n"
        '  "reply": "Tactical spoken radio response as Simon Ghost Riley",\n'
        '  "intent": "task | schedule | reminder | plan | phone | search | agent | core | qa",\n'
        '  "actions": [\n'
        '    {"type": "<action_type>", ...fields}\n'
        '  ]\n'
        "}"
    )


def gemini_voice_reply(text, context):
    """
    Gemini generates the immediate natural language reasoning and spoken replay,
    extracting operational actions across all 9 modules or answering normal Q&A.
    """
    api_key = getattr(settings, 'GEMINI_API_KEY', '') or os.getenv('GEMINI_API_KEY', '')
    if not api_key:
        return None

    models_to_try = [
        os.getenv('GEMINI_MODEL', 'gemini-3.1-flash-lite'),
        'gemini-3.1-flash-lite',
        'gemini-3.8-flash',
        'gemini-2.5-flash',
    ]
    seen = set()
    system_prompt = build_gemini_voice_prompt(context)
    full_prompt = f"{system_prompt}\n\nUSER INPUT: \"{text}\""

    headers = {"Content-Type": "application/json"}
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
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
        try:
            res = requests.post(url, headers=headers, json=payload, timeout=4.5)
            if res.ok:
                data = res.json()
                candidate_text = data['candidates'][0]['content']['parts'][0]['text']
                parsed = clean_json_response(candidate_text)
                if parsed and isinstance(parsed, dict) and 'reply' in parsed:
                    return parsed
            else:
                logger.debug(f"Gemini {model_name} status {res.status_code}")
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
