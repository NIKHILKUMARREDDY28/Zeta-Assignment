
## Task 1 :Overview

Banks receive hundreds of dispute forms daily. This project:

1. **Collects** dispute submissions via a user-facing form.  
2. **Classifies** each dispute (e.g. cards, UPI, net banking).  
3. **Prioritizes** based on VIP status, amount, and fraud risk.  
4. **Routes** to the correct support team with AI-generated next-step recommendations.  

---

## Architecture & Workflow

- **Trigger**: Form submission → workflow engine  
- **AI Agent**: Parses free-text dispute, classifies team & priority, generates an agent note  
- **Switch Node**: Routes to one of:  
  - Card Team  
  - UPI Team  
  - Net Banking Team  
  - ATM Team  
  - Loan Team  
  - Fraud Investigation  
  - General Support  
- **Notifier**: Sends the structured message to the appropriate support mailbox

---

## Workflow Diagram

![Workflow Diagram](assets/task1-workflow-diagram.png)

1. **On form submission**  
2. **AI Agent** (Tools Agent + Chat model)  
3. **Structured Output Parser**  
4. **Switch (Rules)**  
5. **Notification** (Gmail / Slack / internal tool)

---

## AI Agent Prompt

This prompt powers "Zen-Bank Dispute Brain":

```text
You are “Zen-Bank Dispute Brain,” an expert banking-domain triage model.
You will be provided with the customer Query:

    {{ $json["User Query"] }}

**TASK**
1. Read *customer_query*.  
2. Classify the dispute into one of the following team values:
   - card
   - upi
   - net_banking
   - atm
   - loan
   - fraud_investigation
   - general_support

3. Determine priority (high | medium | low) using these rules:
   - HIGH  → VIP customer **or** amount ≥ ₹50,000 **or** potential fraud keywords (“fraud”, “unauthorised”, “scam”).
   - MEDIUM→ amount ₹10,000–49,999 **or** repeat dispute (>2 in six months).
   - LOW   → everything else.

4. Provide **specific next-step advice** (≤40 words) for the support agent.

**OUTPUT (valid JSON)**
```json
{
  "team"           : "<team>",
  "priority"       : "<priority>",
  "agent_note"     : "<short action recommendation>",
  "confidence"     : "<0-1>",
  "chain_of_thought": "<VERY brief reasoning (≤30 words)>"
}

