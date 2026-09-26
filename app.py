import os
import sys
import socket
import gradio as gr
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# ==============================================================================
# 1. CANVA DOMAIN KNOWLEDGE BASE (RAG SOPs & LICENSING RULES)
# ==============================================================================
CANVA_KNOWLEDGE_BASE = [
    {
        "clause_id": "CANVA-SOP-DPI300",
        "category": "Print Resolution & Raster Scaling",
        "content": (
            "SOP CANVA-SOP-DPI300: High-Resolution PDF Print Requirements. To ensure professional "
            "print quality without blurriness, images must maintain at least 300 Effective DPI at final layout size. "
            "When raster images (<150 DPI) are scaled beyond bounding limits, the rendering engine flags a degradation warning. "
            "Remediation: Recommend SVG replacement, replace with original high-res stock asset, or apply automated vectorization."
        )
    },
    {
        "clause_id": "CANVA-LIC-PRO99",
        "category": "Content License Agreement & Export Locks",
        "content": (
            "SOP CANVA-LIC-PRO99: Premium Stock Licensing & Free Tier Restrictions. When a Canva Free account attempts "
            "to export a design containing Pro stock elements, the renderer locks export with 'LICENSED_ASSET_LOCKED'. "
            "Remediation: Free users must either purchase a one-time license token ($1.00 USD), activate a Canva Pro trial, "
            "or support agents can grant a 24-hour one-time goodwill export waiver for urgent non-commercial academic/personal projects."
        )
    },
    {
        "clause_id": "CANVA-RND-VEC500",
        "category": "Vector Complexity & Render Pipeline Memory",
        "content": (
            "SOP CANVA-RND-VEC500: Vector Layer Saturation & SVG Rendering Crashes. Designs containing over 5,000 vector "
            "nodes or nested clip-paths can trigger worker timeout (ERR_RENDER_MEMORY_LIMIT). "
            "Remediation: Clear CDN render cache, isolate corrupted vector paths, or execute automated background layer "
            "flattening (rasterizing decorative background shapes to 300 DPI while preserving editable typography)."
        )
    },
    {
        "clause_id": "CANVA-PRT-BLD125",
        "category": "Print Margins, Bleeds & Crop Marks",
        "content": (
            "SOP CANVA-PRT-BLD125: Industrial Print Bleed Standards. Physical print runs require a standard 0.125-inch (3.175mm) "
            "bleed margin and crop marks to prevent white border trimming defects. "
            "Remediation: Enable 'Show Print Bleed' in editor settings, auto-extend background fills to canvas edge, and enable "
            "PDF-Print export with 'Crop marks and bleed' checked."
        )
    },
    {
        "clause_id": "CANVA-BRD-FNT701",
        "category": "Brand Kit Permissions & Custom Fonts",
        "content": (
            "SOP CANVA-BRD-FNT701: Custom Font Licensing and Team Brand Kit Locks. Custom uploaded OTF/TTF fonts require valid "
            "webfont embedding rights. If a user loses team seat access or brand kit locks are active, PDF export substitutes "
            "unsupported fonts with default open-source fallbacks (e.g., Open Sans). "
            "Remediation: Verify enterprise team seat assignment or convert text elements to vector outlines prior to PDF generation."
        )
    },
    {
        "clause_id": "CANVA-VID-MP4902",
        "category": "Video Engine & Motion Graphics Timeout",
        "content": (
            "SOP CANVA-VID-MP4902: High-Bitrate Video Export Throttling. Video designs exceeding 1080p with multiple concurrent "
            "video tracks or animated transitions can hit the 120-second rendering timeout. "
            "Remediation: Split multi-scene video into sequential render jobs, downsample 4K raw footage to 1080p 60fps, and "
            "re-queue job via dedicated high-priority video rendering instances."
        )
    }
]

docs = [item["content"] for item in CANVA_KNOWLEDGE_BASE]
vectorizer = TfidfVectorizer().fit(docs)
doc_vectors = vectorizer.transform(docs)

def query_canva_rag(query_text: str) -> str:
    """Retrieves grounded Canva SOP clauses based on cosine semantic similarity."""
    query_vec = vectorizer.transform([query_text])
    similarities = cosine_similarity(query_vec, doc_vectors)[0]
    best_idx = similarities.argmax()
    return CANVA_KNOWLEDGE_BASE[best_idx]["content"]

# ==============================================================================
# 2. CANVA MOCK API SUITE & DEFAULT SCENARIO DEFINITIONS
# ==============================================================================
DEFAULT_PROMPT_PRESETS = {
    "1. Print Bleed & Crop Marks Missing": (
        "Commercial print shop rejected our product catalog export because bleed margins and crop marks are missing."
    ),
    "2. Watermark / Pro Asset Paywall Lock": (
        "Export blocked! It says I need to pay for watermarked elements, but this was shared with me by my colleague."
    ),
    "3. Blurry & Low DPI Print Warning": (
        "My wedding invitation PDF looks pixelated and blurry when printed. I need 300 DPI high-res output immediately!"
    ),
    "4. Vector Complexity / Memory Crash": (
        "Export hangs at 99% and then crashes with an ERR_RENDER_MEMORY_LIMIT memory error on my complex illustrated poster."
    ),
    "5. Enterprise Brand Kit Font Overridden": (
        "Our custom corporate font 'Helvetica Now Pro' was replaced with basic Arial during PDF export."
    ),
    "6. 4K Video Render Pipeline Timeout": (
        "Our 60-second marketing reel fails to export to MP4. The progress bar freezes and throws an error."
    )
}

MOCK_CANVA_TICKETS = {
    "CANVA-EXP-101": {
        "user_name": "Sarah Jenkins",
        "user_tier": "Canva Free",
        "design_id": "DAGzQh2m-01",
        "export_format": "PDF-Print",
        "error_code": "LOW_DPI_RESOLUTION_WARNING",
        "query": DEFAULT_PROMPT_PRESETS["3. Blurry & Low DPI Print Warning"]
    },
    "CANVA-LIC-204": {
        "user_name": "Marcus Vance",
        "user_tier": "Canva Free",
        "design_id": "DAGxP98s-02",
        "export_format": "PDF-Standard",
        "error_code": "LICENSED_ASSET_LOCKED",
        "query": DEFAULT_PROMPT_PRESETS["2. Watermark / Pro Asset Paywall Lock"]
    },
    "CANVA-RND-308": {
        "user_name": "Elena Rostova",
        "user_tier": "Canva Pro",
        "design_id": "DAGmB33k-03",
        "export_format": "SVG / Vector",
        "error_code": "ERR_RENDER_MEMORY_LIMIT",
        "query": DEFAULT_PROMPT_PRESETS["4. Vector Complexity / Memory Crash"]
    },
    "CANVA-PRT-415": {
        "user_name": "Apex Marketing",
        "user_tier": "Canva for Teams",
        "design_id": "DAGwK77p-04",
        "export_format": "PDF-Print",
        "error_code": "BLEED_MARGIN_MISSING",
        "query": DEFAULT_PROMPT_PRESETS["1. Print Bleed & Crop Marks Missing"]
    },
    "CANVA-BRD-502": {
        "user_name": "Fintech Global",
        "user_tier": "Canva Enterprise",
        "design_id": "DAGtE12b-05",
        "export_format": "PDF-Standard",
        "error_code": "BRAND_FONT_RESTRICTED",
        "query": DEFAULT_PROMPT_PRESETS["5. Enterprise Brand Kit Font Overridden"]
    },
    "CANVA-VID-603": {
        "user_name": "David Cho",
        "user_tier": "Canva Pro",
        "design_id": "DAGyV54r-06",
        "export_format": "MP4 Video",
        "error_code": "RENDER_PIPELINE_TIMEOUT",
        "query": DEFAULT_PROMPT_PRESETS["6. 4K Video Render Pipeline Timeout"]
    }
}

def tool_inspect_design_manifest(design_id: str) -> dict:
    if "01" in design_id:
        return {"layers": 14, "embedded_fonts": ["Great Vibes"], "min_raster_dpi": 96, "licensed_assets": []}
    elif "02" in design_id:
        return {"layers": 8, "embedded_fonts": ["Montserrat"], "min_raster_dpi": 300, "licensed_assets": ["ASSET_PRO_FLOWER_8892"]}
    elif "03" in design_id:
        return {"layers": 42, "vector_node_count": 8420, "min_raster_dpi": 300, "licensed_assets": []}
    elif "04" in design_id:
        return {"layers": 22, "bleed_enabled": False, "crop_marks": False, "min_raster_dpi": 300, "licensed_assets": []}
    elif "05" in design_id:
        return {"layers": 19, "embedded_fonts": ["Helvetica Now Pro (Custom TTF)"], "license_status": "SEAT_REVOKED"}
    return {"layers": 31, "duration_sec": 60, "video_tracks": 4, "resolution": "4K Ultra HD"}

def tool_verify_asset_licensing(user_tier: str, asset_ids: list) -> dict:
    is_pro = "Pro" in user_tier or "Teams" in user_tier or "Enterprise" in user_tier
    has_premium = len(asset_ids) > 0
    return {
        "user_tier": user_tier,
        "has_premium_assets": has_premium,
        "export_eligible": is_pro or not has_premium,
        "waiver_policy": "Permits 24h courtesy waiver if user is on Free tier for urgent non-commercial export."
    }

def tool_diagnose_render_pipeline(design_id: str, export_format: str) -> dict:
    return {
        "design_id": design_id,
        "export_format": export_format,
        "worker_state": "THROTTLED" if "SVG" in export_format or "MP4" in export_format else "READY",
        "cdn_cache": "DIRTY" if "03" in design_id else "VALID"
    }

def tool_execute_design_remediation(action_type: str, design_id: str) -> str:
    if action_type == "AUTO_VECTORIZE_OR_DOWNSCALE":
        return f"SUCCESS: Enhanced image container and enabled 300 DPI Smart Upscaling for '{design_id}'."
    elif action_type == "APPLY_COURTESY_WAIVER":
        return f"SUCCESS: Issued 24-hour single-use export authorization token for design '{design_id}'."
    elif action_type == "AUTO_FLATTEN_BACKGROUND_VECTORS":
        return f"SUCCESS: Consolidated 8,420 vector nodes in '{design_id}' into flat 300 DPI background layer."
    elif action_type == "INJECT_PRINT_BLEED_AND_MARKS":
        return f"SUCCESS: Injected 0.125\" industrial bleed and aligned vector crop marks for '{design_id}'."
    elif action_type == "RESTORE_BRAND_FONT_BINDING":
        return f"SUCCESS: Verified enterprise seat authentication; rebound custom font 'Helvetica Now Pro'."
    elif action_type == "DOWNMIX_AND_REQUEUE_VIDEO":
        return f"SUCCESS: Downscaled 4K tracks to 1080p 60fps and dispatched to high-priority video render farm."
    return "SUCCESS: Standard triage pipeline executed."

# ==============================================================================
# 3. AUTONOMOUS REACT AGENT WORKFLOW
# ==============================================================================
def run_canva_copilot(ticket_key: str, custom_query: str = "") -> tuple[str, str, str]:
    ticket = MOCK_CANVA_TICKETS[ticket_key]
    user_input = custom_query.strip() if custom_query.strip() else ticket["query"]

    trace = []
    trace.append(f"📥 [Ticket Ingested] {ticket_key} | User: {ticket['user_name']} | Tier: {ticket['user_tier']}")
    trace.append(f"🔍 [Perception] Format: '{ticket['export_format']}' | Error: '{ticket['error_code']}'")
    trace.append(f"💬 [Injected Problem Query] \"{user_input}\"")

    # Step 1: Manifest Inspection
    trace.append(f"⚙️ [Tool Call: Inspect Manifest] Querying canvas element tree for '{ticket['design_id']}'...")
    manifest = tool_inspect_design_manifest(ticket["design_id"])
    trace.append(f"📊 [Observation] Layers: {manifest.get('layers', 'N/A')} | Assets: {manifest.get('licensed_assets', 'None')}")

    # Step 2: Grounded Canva RAG Retrieval
    trace.append(f"📚 [Action: Domain RAG] Searching Canva Knowledge Base for matching SOP...")
    sop_doc = query_canva_rag(user_input + " " + ticket["error_code"])
    trace.append(f"💡 [Observation] Grounded SOP retrieved: {sop_doc[:90]}...")

    # Step 3: Licensing & Telemetry
    trace.append(f"🛡️ [Tool Call: Telemetry & Entitlement] Checking render pipeline & licensing...")
    licensing = tool_verify_asset_licensing(ticket["user_tier"], manifest.get("licensed_assets", []))
    pipeline = tool_diagnose_render_pipeline(ticket["design_id"], ticket["export_format"])
    trace.append(f"📈 [Observation] Export Eligible: {licensing['export_eligible']} | Worker Status: {pipeline['worker_state']}")

    # Step 4: Semantic Routing on the User's Injected Prompt
    if "bleed" in user_input.lower() or "crop" in user_input.lower() or ticket["error_code"] == "BLEED_MARGIN_MISSING":
        remediation_result = tool_execute_design_remediation("INJECT_PRINT_BLEED_AND_MARKS", ticket["design_id"])
        trace.append(f"🚀 [Tool Call: Print Prep Remediation] {remediation_result}")
        work_order = (
            f"### 📋 CANVA SERVICE WORK ORDER: {ticket_key}\n"
            f"**Customer:** {ticket['user_name']} ({ticket['user_tier']}) | **Design ID:** `{ticket['design_id']}`\n"
            f"**Root Cause:** Missing 0.125\" print bleed and crop marks required for industrial print (Triggered: SOP CANVA-PRT-BLD125)\n\n"
            f"#### 1. Autonomous Actions Taken:\n"
            f"- Enabled 'Show Print Bleed' across all canvas pages.\n"
            f"- Extended background artwork to 0.125\" trim boundaries and enabled vector crop marks.\n\n"
            f"#### 2. Customer Resolution Message:\n"
            f"\"Hi {ticket['user_name']}, commercial printers require an extra 1/8-inch margin to prevent white edges during cutting. "
            f"We have updated your design settings, extended background colors to the bleed line, and generated a print-ready PDF "
            f"with embedded trim crop marks that your print shop will accept without issue!\""
        )
    elif "watermark" in user_input.lower() or "pay" in user_input.lower() or "locked" in user_input.lower() or ticket["error_code"] == "LICENSED_ASSET_LOCKED":
        remediation_result = tool_execute_design_remediation("APPLY_COURTESY_WAIVER", ticket["design_id"])
        trace.append(f"🚀 [Tool Call: Licensing Remediation] {remediation_result}")
        work_order = (
            f"### 📋 CANVA SERVICE WORK ORDER: {ticket_key}\n"
            f"**Customer:** {ticket['user_name']} ({ticket['user_tier']}) | **Design ID:** `{ticket['design_id']}`\n"
            f"**Root Cause:** Pro stock element present in Canva Free collaborator export (Triggered: SOP CANVA-LIC-PRO99)\n\n"
            f"#### 1. Autonomous Actions Taken:\n"
            f"- Verified team collaboration context on Free tier account.\n"
            f"- Injected a 24-hour one-time courtesy export pass to bypass the paywall token.\n\n"
            f"#### 2. Customer Resolution Message:\n"
            f"\"Hi {ticket['user_name']}, your colleague included a premium Canva Pro graphic in your shared project. "
            f"To keep your deadline on track, we have issued a 24-hour courtesy export waiver to your account. "
            f"Your PDF is now unlocked and ready to download without watermarks!\""
        )
    elif "font" in user_input.lower() or "arial" in user_input.lower() or ticket["error_code"] == "BRAND_FONT_RESTRICTED":
        remediation_result = tool_execute_design_remediation("RESTORE_BRAND_FONT_BINDING", ticket["design_id"])
        trace.append(f"🚀 [Tool Call: Brand Kit Remediation] {remediation_result}")
        work_order = (
            f"### 📋 CANVA SERVICE WORK ORDER: {ticket_key}\n"
            f"**Customer:** {ticket['user_name']} ({ticket['user_tier']}) | **Design ID:** `{ticket['design_id']}`\n"
            f"**Root Cause:** Brand Kit permissions mismatch causing fallback to default Arial font (Triggered: SOP CANVA-BRD-FNT701)\n\n"
            f"#### 1. Autonomous Actions Taken:\n"
            f"- Re-authenticated enterprise brand kit seat license with customer's organization ID.\n"
            f"- Converted custom typography to embedded vector glyphs to prevent server-side font substitution.\n\n"
            f"#### 2. Customer Resolution Message:\n"
            f"\"Hello {ticket['user_name']}, your design experienced an authentication timeout with your Brand Kit custom font. "
            f"We refreshed your enterprise seat authorization and converted typography to vector outlines for export. "
            f"Your PDF now displays your official font accurately!\""
        )
    elif "video" in user_input.lower() or "mp4" in user_input.lower() or "freeze" in user_input.lower() or ticket["error_code"] == "RENDER_PIPELINE_TIMEOUT":
        remediation_result = tool_execute_design_remediation("DOWNMIX_AND_REQUEUE_VIDEO", ticket["design_id"])
        trace.append(f"🚀 [Tool Call: Video Pipeline Remediation] {remediation_result}")
        work_order = (
            f"### 📋 CANVA SERVICE WORK ORDER: {ticket_key}\n"
            f"**Customer:** {ticket['user_name']} ({ticket['user_tier']}) | **Design ID:** `{ticket['design_id']}`\n"
            f"**Root Cause:** 4K multi-track video stream exceeded 120-second worker render timeout (Triggered: SOP CANVA-VID-MP4902)\n\n"
            f"#### 1. Autonomous Actions Taken:\n"
            f"- Optimized concurrent 4K video streams to 1080p 60fps encoding.\n"
            f"- Dispatched video rendering job to dedicated high-priority video worker pool.\n\n"
            f"#### 2. Customer Resolution Message:\n"
            f"\"Hi {ticket['user_name']}, your video reel contained multiple concurrent 4K tracks that exceeded our standard web renderer limits. "
            f"We optimized the video streams to crisp 1080p 60fps and completed the render on our high-performance queue. "
            f"Your MP4 video is now ready to download!\""
        )
    elif "memory" in user_input.lower() or "hangs" in user_input.lower() or "node" in user_input.lower() or ticket["error_code"] == "ERR_RENDER_MEMORY_LIMIT":
        remediation_result = tool_execute_design_remediation("AUTO_FLATTEN_BACKGROUND_VECTORS", ticket["design_id"])
        trace.append(f"🚀 [Tool Call: Pipeline Remediation] {remediation_result}")
        work_order = (
            f"### 📋 CANVA SERVICE WORK ORDER: {ticket_key}\n"
            f"**Customer:** {ticket['user_name']} ({ticket['user_tier']}) | **Design ID:** `{ticket['design_id']}`\n"
            f"**Root Cause:** Excessive vector complexity (8,420 nodes) exceeding worker memory limit (Triggered: SOP CANVA-RND-VEC500)\n\n"
            f"#### 1. Autonomous Actions Taken:\n"
            f"- Flushed corrupted CDN render cache in Sydney render farm.\n"
            f"- Automatically flattened decorative background vector meshes into sharp 300 DPI raster while preserving crisp typography vectors.\n\n"
            f"#### 2. Customer Resolution Message:\n"
            f"\"Hello {ticket['user_name']}, your complex illustration exceeded the browser SVG node limit during rendering. "
            f"We optimized the design by flattening the dense background decorative nodes into a sharp 300 DPI layer while "
            f"keeping your text fully vector. The export has completed successfully!\""
        )
    else:
        remediation_result = tool_execute_design_remediation("AUTO_VECTORIZE_OR_DOWNSCALE", ticket["design_id"])
        trace.append(f"🚀 [Tool Call: Canvas Remediation] {remediation_result}")
        work_order = (
            f"### 📋 CANVA SERVICE WORK ORDER: {ticket_key}\n"
            f"**Customer:** {ticket['user_name']} ({ticket['user_tier']}) | **Design ID:** `{ticket['design_id']}`\n"
            f"**Root Cause:** Low-resolution raster element (<150 DPI) scaled beyond bounding box (Triggered: SOP CANVA-SOP-DPI300)\n\n"
            f"#### 1. Autonomous Actions Taken:\n"
            f"- Scanned canvas manifest; detected 96 DPI photo scaled 240%.\n"
            f"- Enhanced image container and enabled Smart Resolution Upscaling for PDF-Print export.\n\n"
            f"#### 2. Customer Resolution Message:\n"
            f"\"Hi {ticket['user_name']}, we analyzed your layout. The blurriness was caused by a "
            f"photo element whose resolution dropped below our 300 DPI print standard when enlarged. We've enhanced the container "
            f"and re-rendered your print-ready PDF with optimal resolution. You can now download it directly from your editor!\""
        )

    return "\n\n".join(trace), sop_doc, work_order

# ==============================================================================
# 4. GRADIO INTERFACE DECLARATION WITH PRE-LOADED PROMPTS
# ==============================================================================
with gr.Blocks(theme=gr.themes.Soft(primary_hue="purple")) as demo:
    gr.Markdown("# 🎨 Canva Agentic Service & Design Support Copilot")
    gr.Markdown(
        "Autonomous Customer Support & Design Diagnostic Copilot for **Canva Free, Pro, Teams, and Enterprise**. "
        "Bridges inbound export failure payloads with Canva SOPs, Licensing Agreements, and automated manifest tools."
    )

    with gr.Row():
        with gr.Column(scale=1):
            ticket_dropdown = gr.Dropdown(
                choices=list(MOCK_CANVA_TICKETS.keys()),
                value=list(MOCK_CANVA_TICKETS.keys())[0],
                label="1. Select Inbound Incident Profile"
            )
            preset_picker = gr.Dropdown(
                choices=list(DEFAULT_PROMPT_PRESETS.keys()),
                value=list(DEFAULT_PROMPT_PRESETS.keys())[2],
                label="2. Choose a Default Problem Preset (Auto-fills below)"
            )
            custom_input = gr.Textbox(
                lines=3,
                value=DEFAULT_PROMPT_PRESETS["3. Blurry & Low DPI Print Warning"],
                placeholder="Type or customize your issue prompt here...",
                label="3. Custom Issue Prompt Injection (Live Editable)"
            )
            run_btn = gr.Button("⚡ Run Autonomous Triage & Diagnostics", variant="primary")

            gr.Markdown("### 📊 Target Operating Metrics")
            gr.Markdown(
                "- **Triage Latency:** Reduced from ~20 min to < 30 sec\n"
                "- **Autonomous Resolution:** ~40% tier-1 remediation\n"
                "- **Policy Compliance:** 100% verified on Canva SOPs\n"
                "- **RAM Footprint:** < 35 MB (Serverless micro-runtime)"
            )

        with gr.Column(scale=2):
            with gr.Tabs():
                with gr.TabItem("📋 Minto Work Order & Customer Message"):
                    output_work_order = gr.Markdown()
                with gr.TabItem("🧠 ReAct Agent Diagnostic Trace"):
                    output_trace = gr.Textbox(lines=11, label="Autonomous Tool Calls & Reasoning Trace")
                with gr.TabItem("📖 Grounded Canva SOP (RAG)"):
                    output_rag = gr.Textbox(lines=5, label="Retrieved Engineering & Licensing Guidelines")

    preset_picker.change(
        fn=lambda choice: DEFAULT_PROMPT_PRESETS[choice],
        inputs=[preset_picker],
        outputs=[custom_input]
    )

    run_btn.click(
        fn=run_canva_copilot,
        inputs=[ticket_dropdown, custom_input],
        outputs=[output_trace, output_rag, output_work_order]
    )

# ==============================================================================
# 5. SAFE PORT SCANNER & LAUNCH CALL
# ==============================================================================
def find_available_port(starting_port=7860, max_attempts=50):
    for p in range(starting_port, starting_port + max_attempts):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(('127.0.0.1', p)) != 0:
                return p
    return starting_port

if __name__ == "__main__":
    is_colab = "google.colab" in sys.modules
    env_port = os.environ.get("PORT")

    if env_port:
        port = int(env_port)
        host = "0.0.0.0"
    else:
        port = find_available_port(7860)
        host = "127.0.0.1"

    print(f"🚀 Launching Canva Copilot on http://{host}:{port}")
    demo.launch(
        server_name=host,
        server_port=port,
        inbrowser=True,
        share=is_colab
    )
