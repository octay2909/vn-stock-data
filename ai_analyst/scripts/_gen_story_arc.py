"""Generate updated story_arc.json with correct writing style."""
import sys, io, json, os, re, argparse
from pathlib import Path
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# ---------------------------------------------------------------------------
# CP1 — CLI args: dynamic stem instead of hardcoded constant
# ---------------------------------------------------------------------------
def _parse_args():
    parser = argparse.ArgumentParser(description="Generate story_arc.json for AI Analyst pipeline")
    parser.add_argument("--stem", required=True, help="Dataset stem (e.g. ecommerce_orders_2025)")
    parser.add_argument("--run-id", default=None, help="Pipeline run ID for tracing")
    parser.add_argument("--force", action="store_true", help="Overwrite existing story_arc.json")
    return parser.parse_args()

args = _parse_args()

# CP1 — Sanitize stem
if not re.match(r'^[\w\-\.]+$', args.stem):
    print(f"ERROR: Invalid stem '{args.stem}'", file=sys.stderr)
    sys.exit(1)

stem = args.stem

# ---------------------------------------------------------------------------
# CP5 — Structured logging
# ---------------------------------------------------------------------------
sys.path.insert(0, str(Path(__file__).parent.parent))
from helpers.utils.logger import get_logger, new_run_id

run_id = args.run_id or new_run_id()
log = get_logger(__name__, run_id=run_id, stem=stem)

# ---------------------------------------------------------------------------
# CP1 — Dynamic output path (BASE-anchored, not cwd-relative)
# ---------------------------------------------------------------------------
BASE = Path(__file__).parent.parent
OUT = BASE / f"data/pipeline/{stem}/story_arc.json"

story_arc = {
  "report_type": "pptx",
  "analysis_type": "forecasting",
  "generated_at": "2026-05-28T00:00:00",
  "opening_hook": "Q1 2026 surged +42% but March erased $29K \u2014 seasonal trap or new risk?",
  "scqa": {
    "situation": "Q1 2026 revenue reached $131,360, up +41.8% QoQ, reversing three consecutive quarters of decline. All three customer segments grew QoQ for the first time in four quarters.",
    "complication": "March collapsed to $25,002 \u2014 a -54% MoM drop that removed $29,430 from the quarter. North region drove 86% of the gain and Platform now accounts for 60.6% of revenue, both signaling concentration risk.",
    "question": "What drove Q1 2026 revenue growth, why did March drop, and what is the Q3 2026 forecast?",
    "answer": "March's -54% drop is a confirmed recurring seasonal trough identical to March 2025. Q1 growth is real and volume-driven. Q3 2026 base forecast is $155,869 (+56% YoY). Mitigate Platform and North concentration before Q3."
  },
  "slides": [
    {
      "order": 1, "layout": "COVER",
      "breadcrumb_section": "", "breadcrumb_topic": "",
      "section_color": "#2554E7",
      "headline": "Q1 2026 surged +42% but March erased $29K \u2014 seasonal trap or new risk?",
      "headline_accents": ["+42%", "$29K"],
      "cover_kpis": [
        {"label": "PERIOD", "value": "Jan 2025 \u2013 May 2026"},
        {"label": "ORDERS", "value": "488 orders"},
        {"label": "SEGMENTS", "value": "3 (Enterprise, Mid-Market, SMB)"},
        {"label": "PRODUCTS", "value": "3 (Platform, Analytics, Support)"}
      ],
      "speaker_notes": "Opening hook. Q1 recovered strongly but March created a -54% intra-quarter dip. Two questions: new structural problem? What does Q3 look like?"
    },
    {
      "order": 2, "layout": "BACKGROUND",
      "breadcrumb_section": "Context", "breadcrumb_topic": "Business Context & Analysis Scope",
      "section_color": "#2554E7",
      "headline": "Q1 2026 rebound masked geographic concentration and a sharp seasonal March trough",
      "headline_accents": ["geographic concentration", "seasonal March trough"],
      "left_panel": {
        "supporting_text": "**Overall performance** Q1 2026 delivered $131,360, the strongest quarter since Q2 2025's peak of $136,809.\n\n**Segment growth** All three customer segments grew QoQ for the first time in four quarters.\nMid-Market led at +74%\nEnterprise added +26%\nSMB grew +33%\n\n**What the rebound masked**\nNorth region alone drove 86% of the QoQ dollar gain, jumping from 23.5% to 40.1% revenue share\nPlatform accounted for 60.6% of Q1 revenue after a +72% QoQ surge",
        "supporting_accents": ["$131,360", "+74%", "86%", "60.6%"],
        "chart_id": None, "chart_title": None,
        "key_question": "Q1 2026 rebound masks regional concentration and one deep seasonal trough"
      },
      "right_panel": {
        "supporting_text": "This analysis covers 488 orders from January 2025 through May 2026. Three analytical layers applied: descriptive trend and segment decomposition, diagnostic root cause testing across 5 hypotheses, and Holt-Winters forecasting for Q3 2026.",
        "supporting_accents": ["488 orders", "5 hypotheses"],
        "chart_id": None, "chart_title": None
      },
      "speaker_notes": "Context slide. Establish business situation and scope. Q1 was genuinely strong, but with hidden concentration risk."
    },
    {
      "order": 3, "layout": "FRAMEWORK_3COL",
      "breadcrumb_section": "Approach", "breadcrumb_topic": "Analysis Framework",
      "section_color": "#2554E7",
      "headline": "Three analytical lenses explain what happened, why it happened, and what comes next",
      "headline_accents": ["what happened", "why it happened", "what comes next"],
      "cards": [
        {
          "number": "01", "title": "What Happened",
          "bullets": [
            "**Overall performance** Q1 2026 revenue reached $131,360, up +41.8% QoQ from Q4 2025's $92,669.",
            "**The March trough** March hit $25,002, a drop of -54% vs February, the sharpest single-month decline in the dataset.",
            "**Segment picture** All 3 segments grew QoQ, with North region dominating the dollar gains at +135.5%."
          ],
          "footer": "\u2192 Descriptive: 17 months, 488 orders"
        },
        {
          "number": "02", "title": "Why It Happened",
          "bullets": [
            "**Root cause** Enterprise and Platform withdrawal drove 70% of the March drop, within a confirmed seasonal pattern.",
            "**Seasonality confirmed** March pattern is identical to 2025, confirming structural rather than one-off behavior.",
            "**Hypotheses ruled out** Discounts and churn tested and rejected as contributing causes. 5 hypotheses, 3 rejected."
          ],
          "footer": "\u2192 5 hypotheses tested, 3 rejected"
        },
        {
          "number": "03", "title": "What's Next",
          "bullets": [
            "**Base case** Q3 2026 forecast of $155,869, modeled using Holt-Winters at 8.3% holdout MAPE.",
            "**Forecast range** 95% confidence interval spanning $125K to $179K across three scenarios.",
            "**Key risk variables** North share and Platform QoQ are the two primary swing factors for Q3 outcome."
          ],
          "footer": "\u2192 Q3 2026 forecast, 95% CI: $125K\u2013$179K"
        }
      ],
      "speaker_notes": "Framework slide sets the narrative arc. Three analytical lenses build toward the recommendation."
    },
    {
      "order": 4, "layout": "INSIGHT_CHART",
      "breadcrumb_section": "Context", "breadcrumb_topic": "What's Happening",
      "section_color": "#2554E7",
      "headline": "Q1 2026 reversed three consecutive quarters of decline, marking the strongest rebound in 17 months",
      "headline_accents": ["reversed", "strongest rebound", "17 months"],
      "left_panel": {
        "supporting_text": "Revenue fell three consecutive quarters from the Q2 2025 peak of $136,809 to $92,669 in Q4 2025, a -32% cumulative decline. Q1 2026 reversed course sharply, adding $38,691 (+41.8% QoQ) to reach $131,360, the strongest single-quarter rebound in 17 months.",
        "supporting_accents": ["$136,809", "-32%", "+41.8% QoQ", "$131,360"],
        "chart_id": "quarterly_revenue_trend",
        "chart_title": "Three-quarter slide reversed in Q1 2026 \u2014 revenue recovered to near-peak levels"
      },
      "right_panel": {
        "supporting_text": "January ($51,926) and February ($54,432) were the two strongest consecutive months in the dataset. March dropped sharply to $25,002 (-54% MoM), consistent with prior seasonality. April rebounded to a record $58,003 (+132% MoM), confirming a strong V-shaped recovery.",
        "supporting_accents": ["$51,926", "$54,432", "-54% MoM", "$58,003", "+132% MoM"],
        "chart_id": "monthly_revenue_highlight",
        "chart_title": "March 2026: V-shaped trough \u2014 April sets all-time monthly record at $58K"
      },
      "speaker_notes": "First insight. Lead with quarterly reversal, then show monthly detail to reveal the March trough."
    },
    {
      "order": 5, "layout": "INSIGHT_CHART",
      "breadcrumb_section": "Context", "breadcrumb_topic": "What's Happening",
      "section_color": "#2554E7",
      "headline": "Mid-Market led growth at 74% QoQ, but North drove 86% of the total dollar gain",
      "headline_accents": ["74% QoQ", "North drove 86%"],
      "left_panel": {
        "supporting_text": "All three segments grew QoQ \u2014 the first full-segment rebound in four quarters. Mid-Market was fastest at +74.1% QoQ, contributing 48% of the total $38.7K gain. Enterprise (+26%) and SMB (+33%) also expanded, making Q1 the broadest growth quarter in the dataset.",
        "supporting_accents": ["+74.1% QoQ", "48%", "+26%", "+33%"],
        "chart_id": "segment_qoq_waterfall",
        "chart_title": "Mid-Market added $18.6K \u2014 nearly half the entire Q4-to-Q1 revenue gain"
      },
      "right_panel": {
        "supporting_text": "North surged +135.5% QoQ, jumping from 23.5% to 40.1% of total revenue and contributing 86% of the QoQ dollar gain. South grew +57.7%. East (-10.4%) and West (-11.6%) contracted, showing Q1 growth was geographically concentrated despite strong headline numbers.",
        "supporting_accents": ["+135.5% QoQ", "40.1%", "86%", "+57.7%", "-10.4%", "-11.6%"],
        "chart_id": "region_qoq_slopegraph",
        "chart_title": "North jumped from $21.7K to $54.9K \u2014 East and West both contracted QoQ"
      },
      "speaker_notes": "Segment and region breakdown. Key tension: broad segment growth is real, but geographic concentration in North is a risk."
    },
    {
      "order": 6, "layout": "INSIGHT_CHART",
      "breadcrumb_section": "Context", "breadcrumb_topic": "What's Happening",
      "section_color": "#2554E7",
      "headline": "Platform generated 61% of Q1 revenue \u2014 primary growth engine and largest concentration risk",
      "headline_accents": ["61% of Q1 revenue", "primary growth engine", "largest concentration risk"],
      "left_panel": {
        "supporting_text": "Platform surged +71.8% QoQ to $79,623, contributing 86% of the total QoQ dollar gain and expanding to 60.6% of Q1 revenue. Analytics grew moderately (+36.9%), while Support declined -29.7% as the only contracting product. Platform is now 2.1x larger than Analytics.",
        "supporting_accents": ["+71.8% QoQ", "86%", "60.6%", "+36.9%", "-29.7%"],
        "chart_id": "product_revenue_bar",
        "chart_title": "Platform at $79.6K \u2014 2.1x Analytics, 6.5x Support; Support the only product declining"
      },
      "right_panel": {
        "supporting_text": "With 60.6% of total revenue, Platform has become a major single-product dependency. In March, Platform fell -60.6% and accounted for 73.2% of the monthly revenue drop, amplifying the seasonal trough. Any Platform slowdown in Q3 would disproportionately impact overall performance.",
        "supporting_accents": ["60.6%", "-60.6%", "73.2%"],
        "chart_id": "product_concentration_heatmap",
        "chart_title": "Platform dominates every month of Q1 \u2014 March collapse came entirely from Platform drop"
      },
      "speaker_notes": "Product dimension. Platform's dominance drives both Q1 growth and amplifies every seasonal dip."
    },
    {
      "order": 7, "layout": "FINDINGS_OVERVIEW",
      "breadcrumb_section": "Findings", "breadcrumb_topic": "Overview",
      "section_color": "#EF4444",
      "headline": "Three data-backed root causes explain the March decline",
      "headline_accents": ["Three data-backed root causes"],
      "cards": [
        {
          "number": "01", "title": "Seasonal Demand Trough",
          "bullets": [
            "**The pattern** March fell -54% in both 2025 and 2026, confirming a structural seasonal trough rather than a one-off event.",
            "**The mechanism** B2B budget freeze at fiscal year boundary drives Enterprise and Mid-Market buyers to defer purchases.",
            "**The recovery signal** April recovered V-shaped both years, confirming demand is deferred, not lost."
          ],
          "footer": "H1 confirmed: accounts for 100% of drop"
        },
        {
          "number": "02", "title": "Enterprise Withdrawal",
          "bullets": [
            "**The scale** Enterprise dropped from 9 orders to 4 in March, with revenue falling -86.4%.",
            "**The concentration** Enterprise and Mid-Market together drove 109% of the total March revenue drop.",
            "**The offset** SMB grew +21% but only partially masked the severity of the Enterprise decline."
          ],
          "footer": "H2 confirmed: mechanism within H1"
        },
        {
          "number": "03", "title": "Platform Concentration",
          "bullets": [
            "**The impact** Platform fell -60.6%, losing $21.5K in March alone.",
            "**The dominance** Platform drove 73.2% of the total revenue drop, the single largest contributing factor.",
            "**The paradox** AOV compressed from $1,869 to $1,270 per order, while the same product powers Q1 growth."
          ],
          "footer": "Amplified H2 \u2014 same product powers Q1 growth"
        }
      ],
      "speaker_notes": "Overview presenting all three root causes before deep-diving. Pyramid apex for the diagnostic section."
    },
    {
      "order": 8, "layout": "INSIGHT_CHART",
      "breadcrumb_section": "Root Cause #1", "breadcrumb_topic": "Seasonal Trough",
      "section_color": "#EF4444",
      "headline": "March declined fifty-four percent in both 2025 and 2026, confirming a recurring B2B seasonal pattern",
      "headline_accents": ["fifty-four percent", "both 2025 and 2026", "recurring B2B seasonal"],
      "left_panel": {
        "supporting_text": "March declines were nearly identical in both years: -54.0% in 2025 vs -54.1% in 2026, with order counts dropping similarly and April fully rebounding each time. The repeated pattern confirms a structural seasonal effect rather than a one-off event.",
        "supporting_accents": ["-54.0%", "-54.1%", "fully rebounding"],
        "chart_id": "march_seasonal_comparison",
        "chart_title": "Feb-Mar-Apr pattern repeats in 2025 and 2026 \u2014 magnitude identical, recovery confirmed"
      },
      "right_panel": {
        "supporting_text": "The March decline was broad-based across regions: North (-45.7%), East (-80.2%), and South (-69.2%) collectively drove 98.9% of the drop, while West remained relatively stable. The cross-region pattern confirms a structural B2B seasonal pause rather than a company-specific issue.",
        "supporting_accents": ["-45.7%", "-80.2%", "-69.2%", "98.9%"],
        "chart_id": "march_region_drop_bar",
        "chart_title": "North, East, South all fell 46\u201380% in March \u2014 geographic breadth rules out internal cause"
      },
      "speaker_notes": "Root Cause #1. Evidence: two-year identical pattern + geographic breadth. Both confirm seasonal, not structural."
    },
    {
      "order": 9, "layout": "INSIGHT_CHART",
      "breadcrumb_section": "Root Cause #2", "breadcrumb_topic": "Enterprise Withdrawal",
      "section_color": "#EF4444",
      "headline": "Enterprise fell from 9 to 4 orders in March, driving 68% of the total revenue loss",
      "headline_accents": ["9 to 4 orders", "68% of the total revenue loss"],
      "left_panel": {
        "supporting_text": "The March decline was driven primarily by Enterprise (-86.4%) and Mid-Market (-66.2%), which together contributed over 100% of the total revenue drop. In contrast, SMB grew +21.3%, partially offsetting the decline and masking the severity of the upper-segment slowdown.",
        "supporting_accents": ["-86.4%", "-66.2%", "over 100%", "+21.3%"],
        "chart_id": "march_segment_waterfall",
        "chart_title": "Enterprise and Mid-Market pulled out $32.2K; SMB added $2.7K back \u2014 net drop $29.4K"
      },
      "right_panel": {
        "supporting_text": "The March decline was driven mainly by an order-count shortfall, with 11 fewer orders explaining 66% of the revenue drop. The missing orders were disproportionately high-value Enterprise and Platform deals, while higher discounting had minimal impact.",
        "supporting_accents": ["11 fewer orders", "66%"],
        "chart_id": "march_volume_aov_decomposition",
        "chart_title": "Volume shortfall (66%) and AOV compression (34%) fully account for the $29.4K March drop"
      },
      "speaker_notes": "Root Cause #2. Enterprise withdrawal is the mechanism through which seasonality hits hardest."
    },
    {
      "order": 10, "layout": "INSIGHT_CHART",
      "breadcrumb_section": "Root Cause #3", "breadcrumb_topic": "Platform Concentration",
      "section_color": "#EF4444",
      "headline": "Platform drove 73% of March's decline, while the same product powering Q1 also amplified the seasonal trough",
      "headline_accents": ["73% of March's decline", "amplified the seasonal trough"],
      "left_panel": {
        "supporting_text": "Platform drove 73.2% of the March revenue decline, falling -60.6% as both order volume and AOV weakened. While all product lines declined, the scale of Platform's revenue share amplified the overall seasonal downturn.",
        "supporting_accents": ["73.2%", "-60.6%"],
        "chart_id": "platform_feb_mar_comparison",
        "chart_title": "Platform collapsed from $35.5K to $14.0K in March \u2014 drove nearly three-quarters of the drop"
      },
      "right_panel": {
        "supporting_text": "Platform concentration is accelerating \u2014 rising from 55% of revenue in Q1 2025 to 60.6% in Q1 2026. The same dynamic driving Platform's growth also amplifies downside risk, making it the largest risk factor for Q3 2026 performance.",
        "supporting_accents": ["55%", "60.6%"],
        "chart_id": "product_share_trend",
        "chart_title": "Platform share rose from 50% in Q4 2025 to 61% in Q1 2026 \u2014 concentration accelerating"
      },
      "speaker_notes": "Root Cause #3. Platform's dominance is a double-edged story: drives Q1 growth and amplifies every seasonal dip."
    },
    {
      "order": 11, "layout": "FRAMEWORK_3COL",
      "breadcrumb_section": "Findings", "breadcrumb_topic": "Hypotheses Tested",
      "section_color": "#EF4444",
      "headline": "Three competing explanations were tested and rejected through data-backed evidence",
      "headline_accents": ["tested and rejected", "data-backed evidence"],
      "cards": [
        {
          "number": "01", "title": "Discounts: Rejected",
          "bullets": [
            "**The hypothesis** Higher discount rates drove the March revenue drop.",
            "**The evidence** Discount rate rose only +2.3pp, with revenue impact of just -$682, representing 2.3% of the total $29,430 drop.",
            "**The verdict** The higher discount rate reflects an SMB order mix shift, not price cuts. Negligible as a root cause."
          ],
          "footer": "\u2192 Rejected: explains 2% of drop only"
        },
        {
          "number": "02", "title": "Churn: Rejected",
          "bullets": [
            "**The hypothesis** Customer churn drove the reduction in March order volume.",
            "**The evidence** March 2026 churn rate was 0.200, the second-lowest ever recorded. Q1 2026 average churn improved from 0.381 in Q4 to 0.159.",
            "**The verdict** Churn affected AOV slightly but had no meaningful impact on order volume."
          ],
          "footer": "\u2192 Rejected: explains 5% of AOV effect only"
        },
        {
          "number": "03", "title": "Discount Pull-Forward: Rejected",
          "bullets": [
            "**The hypothesis** Q1 growth was manufactured by pulling demand forward through heavy discounting.",
            "**The evidence** Q4 discount rate was 13.6% vs Q1 at 14.0%, essentially flat. Q1 volume grew by 19 net new orders and AOV rose from $1,404 to $1,545.",
            "**The verdict** No pull-forward detected. Q1 growth reflects genuine demand, not a pricing artifact."
          ],
          "footer": "\u2192 Rejected: Q1 growth is real, not manufactured"
        }
      ],
      "speaker_notes": "Ruling out slide. Rigorous hypothesis testing builds credibility. Tested and rejected, not just ignored."
    },
    {
      "order": 12, "layout": "INSIGHT_CHART",
      "breadcrumb_section": "Predict", "breadcrumb_topic": "Q3 2026 Forecast",
      "section_color": "#EF4444",
      "headline": "Q3 2026 base forecast is $155,869, up 56% YoY, with outcomes ranging from $125K to $179K",
      "headline_accents": ["$155,869", "56% YoY", "$125K to $179K"],
      "left_panel": {
        "supporting_text": "The Holt-Winters forecast projects Q3 2026 at $155.9K (+55.6% YoY vs Q3 2025), with August expected to be the peak month before a softer September. The outlook assumes continued North region strength and sustained Platform growth momentum.",
        "supporting_accents": ["$155.9K", "+55.6% YoY"],
        "chart_id": "q3_forecast_line",
        "chart_title": "Q3 2026 forecast: $155.9K base \u2014 Jul $54.7K, Aug $62.3K, Sep $38.8K"
      },
      "right_panel": {
        "supporting_text": "The forecast carries meaningful uncertainty, with July 2026's 95% confidence interval ranging from $38.6K to $70.8K. Given the limited 17-month training history, projections should be treated as directional, with downside risk tied to weaker North or Platform performance.",
        "supporting_accents": ["$38.6K", "$70.8K"],
        "chart_id": "forecast_scenario_bar",
        "chart_title": "Base $155.9K sits between pessimistic $124.7K and optimistic $179.3K \u2014 North/Platform are the swing"
      },
      "speaker_notes": "Forecast slide. Lead with headline number, then communicate uncertainty honestly."
    },
    {
      "order": 13, "layout": "INSIGHT_CHART",
      "breadcrumb_section": "Predict", "breadcrumb_topic": "Model Validation",
      "section_color": "#EF4444",
      "headline": "Holt-Winters outperformed all three competing models, beating the naive seasonal baseline by 42%",
      "headline_accents": ["outperformed all three", "42%"],
      "left_panel": {
        "supporting_text": "Among four forecasting models tested on the Mar-May 2026 holdout, Holt-Winters performed best with 8.3% MAPE, outperforming STL (10.4%), the seasonal baseline (14.1%), and ETS (24.9%). Its stronger accuracy indicates it captured the B2B seasonal pattern most effectively.",
        "supporting_accents": ["8.3% MAPE", "10.4%", "14.1%", "24.9%"],
        "chart_id": "model_comparison_mape",
        "chart_title": "Holt-Winters MAPE 8.3% \u2014 42% improvement over naive seasonal, 67% better than ETS"
      },
      "right_panel": {
        "supporting_text": "The winning model predicted March 2026 and May 2026 with near-perfect accuracy, but underestimated April's sharp rebound by 24%. The model is most reliable during seasonal troughs and stable periods, while sudden recovery spikes carry higher uncertainty.",
        "supporting_accents": ["March 2026", "May 2026", "24%"],
        "chart_id": "holdout_actual_vs_pred",
        "chart_title": "March and May near-exact; April recovery spike harder to call \u2014 inherent in V-shape uncertainty"
      },
      "speaker_notes": "Model validation. Build trust in the forecast by showing the model earned its place against competitors."
    },
    {
      "order": 14, "layout": "CONCLUSIONS_OVERVIEW",
      "breadcrumb_section": "Conclusions", "breadcrumb_topic": "Key Takeouts",
      "section_color": "#2554E7",
      "headline": "Three conclusions: March seasonality is predictable, concentration risk is manageable, and Q3 outlook is strong but conditional",
      "headline_accents": ["March seasonality is predictable", "concentration risk is manageable", "Q3 outlook is strong"],
      "cards": [
        {
          "number": "01", "title": "March: Plan for It",
          "bullets": [
            "**The pattern is structural** March's -54% decline is confirmed across two consecutive years, making it predictable and plannable.",
            "**The action** Front-load Enterprise deals into Jan-Feb, where each order averages $2,569 in protected revenue.",
            "**The recovery signal** April consistently rebounds, indicating March reflects deferred demand rather than lost revenue."
          ],
          "footer": "Act now: Jan-Feb window is the only defense"
        },
        {
          "number": "02", "title": "Concentration: Watch It",
          "bullets": [
            "**The risk** North and Platform drove 86% of Q1 growth, highlighting dangerously concentrated recovery dynamics.",
            "**The gap** East and West declined, reinforcing the need for stronger regional diversification before Q3.",
            "**The warning sign** Support fell -30% QoQ, signaling growing product-line risk that needs to be addressed mid-term."
          ],
          "footer": "Mid-term: diversify before concentration bites"
        },
        {
          "number": "03", "title": "Q3: Base Case Is Strong",
          "bullets": [
            "**The forecast** Q3 2026 base case of $155.9K, representing +56% YoY vs Q3 2025.",
            "**The range** Forecast spans from $124.7K downside to $179.3K upside, a $54K gap driven by execution.",
            "**The swing factors** Platform and North remain the two primary variables determining which scenario unfolds."
          ],
          "footer": "Monitor monthly: alert if >30% miss or North < 25%"
        }
      ],
      "speaker_notes": "Three conclusions. Urgency-tiered: March is immediate (Jan-Feb window), concentration is mid-term, Q3 is conditional."
    },
    {
      "order": 15, "layout": "STRATEGY_MAPS",
      "breadcrumb_section": "Action", "breadcrumb_topic": "Three-Phase Roadmap",
      "section_color": "#42967A",
      "headline": "Three-phase roadmap: stabilize March risk, diversify growth by Q3, and monitor forecasts monthly",
      "headline_accents": ["stabilize March risk", "diversify growth", "monitor forecasts"],
      "cards": [
        {
          "number": "01", "title": "Defend March (30 days)",
          "bullets": [
            "**The target** Front-load $20K+ committed Enterprise in Jan-Feb to buffer against March's structural -54% decline.",
            "**The leverage** Each Enterprise order averages $2,569, making early deal stacking the strongest revenue cushion available.",
            "**The alert** If Feb Enterprise pipeline falls below $18K, escalate immediately before the window closes."
          ],
          "footer": "Owner: Sales \u2014 Jan-Feb window only"
        },
        {
          "number": "02", "title": "Diversify Growth (90 days)",
          "bullets": [
            "**The priority accounts** Assign AEs to top 5 lapsed accounts in East and West, the fastest near-term recovery opportunity after Q1 declines.",
            "**The product play** Build an upsell roadmap for Analytics and Support, both currently underweighted relative to their potential.",
            "**The concentration target** Drive Platform share below 55% by end of Q3 to reduce single-product dependency."
          ],
          "footer": "Owner: GTM \u2014 reduce single-product risk"
        },
        {
          "number": "03", "title": "Monitor Q3 Monthly",
          "bullets": [
            "**The forecast guard** Flag any monthly actuals vs forecast variance exceeding 30%, early detection protects the $155.9K base case.",
            "**The North signal** Trigger a full review if North share drops below 25%, a key Q3 swing factor alongside Platform.",
            "**The recalibration trigger** If Platform QoQ turns negative, initiate full forecast recalibration immediately without waiting for quarter-end."
          ],
          "footer": "Owner: Analytics \u2014 monthly review cadence"
        }
      ],
      "speaker_notes": "Three-phase roadmap. Phase 1 is time-bound (Jan-Feb), Phase 2 is strategic (Q3 deadline), Phase 3 is ongoing."
    },
    {
      "order": 16, "layout": "RECS_TABLE",
      "breadcrumb_section": "Action", "breadcrumb_topic": "Recommendations",
      "section_color": "#42967A",
      "headline": "Five specific actions \u2014 two immediate with hard deadlines, two strategic, one ongoing",
      "headline_accents": ["two immediate", "hard deadlines"],
      "rows": [
        {"priority": "P1-Now", "action": "Front-load Enterprise pipeline in Jan-Feb 2027: target $20K+ in committed Enterprise orders by Feb 15 to offset March seasonal withdrawal", "owner": "Sales VP", "timeline": "By Feb 15, 2027", "expected_impact": "Reduces March 2027 drop by 20-30%", "success_metric": "Feb 2027 Enterprise pipeline > $20K committed"},
        {"priority": "P1-Now", "action": "Launch monthly forecast vs actuals review: implement variance tracking and trigger model recalibration if any month misses point estimate by more than 30%", "owner": "Analytics Lead", "timeline": "Live by June 30, 2026", "expected_impact": "Early Q3 warning system active before July", "success_metric": "Monthly variance report delivered by 10th of each month"},
        {"priority": "P2-Next", "action": "Assign dedicated AEs to top 5 lapsed accounts in East and West regions; set Q2 2026 recovery target of more than 10% QoQ growth for each region", "owner": "Sales/GTM", "timeline": "Q2 2026 (by June 30)", "expected_impact": "East + West combined share rises toward 40%", "success_metric": "East + West combined revenue share > 38% in Q2 2026"},
        {"priority": "P2-Next", "action": "Build Analytics and Support upsell roadmap with quarterly revenue targets to reduce Platform concentration from 60.6% toward 55% by Q3 2026", "owner": "Product/Sales", "timeline": "Q3 2026 (by Sep 30)", "expected_impact": "Platform share below 55% by Q3 2026", "success_metric": "Platform revenue share < 55% in Q3 2026"},
        {"priority": "P3-Watch", "action": "Monitor North region revenue share monthly; escalate if share drops below 25% or Platform QoQ growth turns negative for two consecutive months", "owner": "Analytics Lead", "timeline": "Ongoing from June 2026", "expected_impact": "Q3 concentration risk flagged 4-6 weeks early", "success_metric": "North share > 25% and Platform QoQ > 0% each month"}
      ],
      "speaker_notes": "Recommendations table. Two P1-Now items have hard deadlines. The rest are strategic and ongoing."
    },
    {
      "order": 17, "layout": "IMPACT_TWO_COL",
      "breadcrumb_section": "Action", "breadcrumb_topic": "Expected Impact",
      "section_color": "#42967A",
      "headline": "Execute the playbook and Q3 lands near $179K, ignore it and risk $124K",
      "headline_accents": ["$179K", "$124K"],
      "left_panel": {
        "title": "Why Front-Load Enterprise",
        "supporting_text": "**The core mechanic:** Front-loading Enterprise pipeline in Jan\u2013Feb is the highest-leverage near-term action available.\n\n**What each deal is worth:**\nEach additional Enterprise order in February = ~$2,569 in revenue (Feb 2026 Enterprise AOV)\nShifting just 5 Enterprise deals from March to Jan/Feb recovers an estimated $10\u2013$13K of the typical March shortfall\nEquivalent to reducing the March drop from -54% toward -38%\n\n**Why January matters most:** January is the most efficient month to close Enterprise renewals, before the Q1/Q2 planning freeze sets in.",
        "supporting_accents": ["$2,569", "$10\u2013$13K", "-54%", "-38%"],
        "chart_id": None, "chart_title": None
      },
      "right_panel": {
        "title": "Q3 Scenario Range",
        "supporting_text": "**Base case \u2014 $155.9K:** Assumes North holds above 35% revenue share and Platform QoQ growth stays positive.\n\n**Optimistic case \u2014 $179.3K (+15%):** Requires Mid-Market and North to maintain Q1 2026 pace through Q3.\n\n**Pessimistic case \u2014 $124.7K (-20%):** Models reversion to Q4 2025 growth rates \u2014 a realistic downside if Platform normalizes.\n\nThe $54K gap between pessimistic and optimistic is the financial stake of the recommended actions.\n\n**Early warning triggers:**\nMonthly miss > 30% vs forecast\nNorth share below 25%\nPlatform QoQ turning negative",
        "supporting_accents": ["$155.9K", "$179.3K", "$124.7K", "$54K"],
        "chart_id": None, "chart_title": None
      },
      "speaker_notes": "Impact slide. Make the financial stakes concrete: the $54K gap is the value of executing the recommendations."
    }
  ],
  "chart_requirements": [
    {"chart_id": "quarterly_revenue_trend", "chart_type": "highlight_line", "data_source": "descriptive_output", "slide_order": 4, "section": "descriptive", "data": {"x": ["Q1'25","Q2'25","Q3'25","Q4'25","Q1'26"], "y": [113379.36,136809.46,100191.33,92668.96,131359.96], "highlight_range": [1,3], "highlight_points": [4], "value_format": "K"}},
    {"chart_id": "monthly_revenue_highlight", "chart_type": "highlight_line", "data_source": "descriptive_output", "slide_order": 4, "section": "descriptive", "data": {"x": ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec","Jan'26","Feb'26","Mar'26","Apr'26","May'26"], "y": [42619.67,48467.44,22292.25,42065.79,53020.16,41723.51,27460.48,38980.49,33750.36,35893.72,18911.03,37864.21,51925.71,54432.15,25002.10,58002.68,55289.61], "highlight_range": [12,16], "highlight_points": [14], "value_format": "K"}},
    {"chart_id": "segment_qoq_waterfall", "chart_type": "waterfall", "data_source": "descriptive_output", "slide_order": 5, "section": "descriptive", "data": {"categories": ["Q4 2025","Mid-Market","SMB","Enterprise","Q1 2026"], "values": [92668.96,18624.96,11670.24,8395.81,131359.96], "start_value": 92668.96, "value_format": "K"}},
    {"chart_id": "region_qoq_slopegraph", "chart_type": "slopegraph", "data_source": "descriptive_output", "slide_order": 5, "section": "descriptive", "data": {"labels": ["North","South","East","West"], "before": [21745.60,19363.57,27925.50,23634.28], "after": [54925.61,30528.46,25011.24,20894.66], "before_label": "Q4 2025", "after_label": "Q1 2026", "highlight": ["North"]}},
    {"chart_id": "product_revenue_bar", "chart_type": "vertical_bar", "data_source": "descriptive_output", "slide_order": 6, "section": "descriptive", "data": {"categories": ["Platform","Analytics","Support"], "values": [79622.85,39412.83,12324.28], "highlight": ["Platform"], "value_format": "K"}},
    {"chart_id": "product_concentration_heatmap", "chart_type": "heatmap", "data_source": "descriptive_output", "slide_order": 6, "section": "descriptive", "data": {"rows": ["Platform","Analytics","Support"], "cols": ["Jan'26","Feb'26","Mar'26"], "values": [[38000,35503,13972],[13000,11433,8181],[5000,7496,2849]], "colormap": "Blues"}},
    {"chart_id": "march_seasonal_comparison", "chart_type": "grouped_bar", "data_source": "diagnostic_output", "slide_order": 8, "section": "diagnostic", "data": {"categories": ["Feb","Mar","Apr"], "groups": [{"name": "2025", "values": [48467.44,22292.25,42065.79], "highlight": False},{"name": "2026", "values": [54432.15,25002.10,58002.68], "highlight": True}]}},
    {"chart_id": "march_region_drop_bar", "chart_type": "horizontal_bar", "data_source": "diagnostic_output", "slide_order": 8, "section": "diagnostic", "data": {"categories": ["East","South","North","West"], "values": [-80.2,-69.2,-45.7,-5.1], "highlight": ["East","South","North"], "value_format": "%"}},
    {"chart_id": "march_segment_waterfall", "chart_type": "waterfall", "data_source": "diagnostic_output", "slide_order": 9, "section": "diagnostic", "data": {"categories": ["Feb 2026","Enterprise","Mid-Market","SMB","Mar 2026"], "values": [54432.15,-19987.95,-12184.80,2742.69,25002.10], "start_value": 54432.15, "value_format": "K"}},
    {"chart_id": "march_volume_aov_decomposition", "chart_type": "waterfall", "data_source": "diagnostic_output", "slide_order": 9, "section": "diagnostic", "data": {"categories": ["Feb Rev","Volume Effect","AOV Effect","Interaction","Mar Rev"], "values": [54432.15,-19314.64,-15678.90,5563.48,25002.10], "start_value": 54432.15, "value_format": "K"}},
    {"chart_id": "platform_feb_mar_comparison", "chart_type": "grouped_bar", "data_source": "diagnostic_output", "slide_order": 10, "section": "diagnostic", "data": {"categories": ["Platform","Analytics","Support"], "groups": [{"name": "Feb 2026", "values": [35503.00,11433.19,7495.97], "highlight": False},{"name": "Mar 2026", "values": [13972.09,8181.10,2848.91], "highlight": True}]}},
    {"chart_id": "product_share_trend", "chart_type": "multi_line", "data_source": "diagnostic_output", "slide_order": 10, "section": "diagnostic", "data": {"x": ["Q1'25","Q2'25","Q3'25","Q4'25","Q1'26"], "series": [{"name": "Platform", "values": [55.0,57.0,52.0,50.0,60.6], "highlight": True},{"name": "Analytics", "values": [30.0,28.0,33.0,31.0,30.0], "highlight": False},{"name": "Support", "values": [15.0,15.0,15.0,19.0,9.4], "highlight": False}]}},
    {"chart_id": "q3_forecast_line", "chart_type": "forecast_line", "data_source": "predictive_output", "slide_order": 12, "section": "predictive", "data": {"x": ["Jan'25","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec","Jan'26","Feb","Mar","Apr","May","Jul'26","Aug","Sep"], "historical": [42619.67,48467.44,22292.25,42065.79,53020.16,41723.51,27460.48,38980.49,33750.36,35893.72,18911.03,37864.21,51925.71,54432.15,25002.10,58002.68,55289.61,None,None,None], "forecast": [None,None,None,None,None,None,None,None,None,None,None,None,None,None,None,None,None,54680.24,62349.08,38839.86], "ci_low": [None,None,None,None,None,None,None,None,None,None,None,None,None,None,None,None,None,38560.5,46229.33,22720.11], "ci_high": [None,None,None,None,None,None,None,None,None,None,None,None,None,None,None,None,None,70799.99,78468.83,54959.60], "split_idx": 17}},
    {"chart_id": "forecast_scenario_bar", "chart_type": "vertical_bar", "data_source": "predictive_output", "slide_order": 12, "section": "predictive", "data": {"categories": ["Pessimistic","Base Case","Optimistic"], "values": [124695.34,155869.18,179249.56], "highlight": ["Base Case"], "value_format": "K"}},
    {"chart_id": "model_comparison_mape", "chart_type": "model_comparison_bar", "data_source": "predictive_output", "slide_order": 13, "section": "predictive", "data": {"models": ["Holt-Winters","STL","Naive Seasonal","ETS"], "scores": [8.27,10.37,14.14,24.95], "metric_name": "MAPE (%)", "highlight": ["Holt-Winters"]}},
    {"chart_id": "holdout_actual_vs_pred", "chart_type": "grouped_bar", "data_source": "predictive_output", "slide_order": 13, "section": "predictive", "data": {"categories": ["Mar 2026","Apr 2026","May 2026"], "groups": [{"name": "Actual", "values": [25002.10,58002.68,55289.61], "highlight": False},{"name": "Holt-Winters", "values": [24864.80,44302.29,54942.60], "highlight": True}]}}
  ],
  "confidence": {"score": 82, "grade": "B"},
  "metadata": {"total_slides": 17, "analysis_type": "forecasting", "total_findings": 6}
}

# ---------------------------------------------------------------------------
# CP3 — Skip-if-exists + --force guard
# ---------------------------------------------------------------------------
if OUT.exists() and not args.force:
    log.info("story_arc_exists_skip", path=str(OUT))
    print(f"[skip] {OUT} already exists. Use --force to overwrite.")
    sys.exit(0)

if OUT.exists() and args.force and sys.stdin.isatty():
    answer = input(f"[HITL] Overwrite {OUT}? [y/N] ").strip().lower()
    if answer != "y":
        log.info("story_arc_overwrite_cancelled", path=str(OUT))
        sys.exit(0)

# ---------------------------------------------------------------------------
# CP4 — Error-handled write
# ---------------------------------------------------------------------------
try:
    os.makedirs(OUT.parent, exist_ok=True)
    with open(OUT, 'w', encoding='utf-8') as f:
        json.dump(story_arc, f, ensure_ascii=False, indent=2)
except OSError as exc:
    log.error("story_arc_write_failed", path=str(OUT), error=str(exc))
    sys.exit(1)

# CP5 — Structured log on success
log.info("story_arc_written", path=str(OUT), slide_count=len(story_arc["slides"]))
print(f"Slides: {len(story_arc['slides'])}, Charts: {len(story_arc['chart_requirements'])}")

# Quick validation: check key bullets
for s in story_arc['slides']:
    if s.get('cards'):
        for c in s['cards']:
            for b in c.get('bullets', []):
                if b.startswith('**') and (' — ' in b[:30] or ': ' in b[:30]):
                    # Check if separator is between bold and prose
                    bold_end = b.find('**', 2)
                    if bold_end > 0:
                        after_bold = b[bold_end+2:bold_end+5]
                        if after_bold.startswith(' \u2014') or after_bold.startswith(':'):
                            log.warning("bad_bullet_separator", slide=s['order'], bullet=b[:60])
log.info("validation_done")
