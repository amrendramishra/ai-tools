# Email 1: Welcome & Quick Start
**Timing:** Day 0 - Immediately after signup
**Goal:** Get user to first value in 5 minutes

---

**Subject:** You're in! Here's your 5-minute quick start 🚀
**Subject A/B:** Welcome to [Product] - let's ship your first AI review
**Subject B/B:** Your API key is ready. Let's go.

**Preview text:** Get your first AI code review in under 5 minutes.

---

Hi {{first_name}},

Welcome to [Product]! Your account is ready.

Here's the fastest path to your first AI-powered code review:

```bash
# 1. Set your API key
export PRODUCT_API_KEY={{api_key}}

# 2. Submit code for review
curl -X POST https://api.product.com/v1/code/review \
  -H "Authorization: Bearer $PRODUCT_API_KEY" \
  -d '{"code": "def add(a, b): return a + b", "language": "python"}'
```

That's it. You'll get back:
- Code quality score
- Suggested improvements
- Security vulnerabilities (if any)
- Test suggestions

**→ [Try it in the Dashboard]({{dashboard_url}})**

Questions? Reply to this email - it goes straight to my inbox.

Cheers,
{{founder_name}}
Founder, [Product]

P.S. - We have a Slack community with 500+ developers. [Join here]({{slack_url}})
