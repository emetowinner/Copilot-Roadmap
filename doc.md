

# Copilot GA vs Non‑GA Roadmap Visibility

## 1. Problem They Are Trying to Solve

Leadership (via Paul → Jeff) needs **clarity and confidence** when discussing Copilot internally and with stakeholders:

*   What Copilot capabilities can we **safely rely on today (GA)**?
*   Which ones are **preview / targeted / frontier**, and therefore risky?
*   When will non‑GA features realistically become GA?
*   Why certain Copilot features are **not visible**, **not enabled**, or **not ready** yet

This is **not discoverable** from the admin center alone and is painful to interpret on the raw Microsoft roadmap site.

***

## 2. The Proposed Solution (Correct Interpretation)

### 🎯 A “Copilot Feature Readiness & Roadmap Lens”

A **single authoritative artefact** that consolidates Microsoft’s roadmap data and clearly classifies Copilot capabilities by:

*   **Availability State**
*   **Risk Level**
*   **Expected GA Window**
*   **Deployment Readiness**

This becomes:

*   A **talking document for leadership**
*   A **source of truth for IT**
*   A **deflection tool** for “why can’t Copilot do X yet?”

***

## 3. What the Solution Actually Looks Like

### 3.1 Core Deliverable

A **structured Copilot Feature Matrix**, delivered as:

*   Excel / SharePoint list / lightweight web view (prototype)
*   With automation-ready structure

Each row represents a **Copilot capability**, not a product.

***

### 3.2 Example Feature Categories

Features are grouped logically, such as:

*   Copilot in Word / Excel / PowerPoint
*   Copilot in Teams
*   Agentic capabilities (Agent Mode, Cowork, Agent 365)
*   Copilot extensibility (Copilot Studio, declarative agents)
*   Governance & admin controls
*   Models and reasoning features (Researcher, Critique, multimodel)

***

### 3.3 Required Columns (This Is the Value)

Each feature entry includes:

*   **Feature name**
*   **Workload** (Word, Excel, Teams, Platform, etc.)
*   **Release status**
    *   GA
    *   Targeted Release
    *   Preview
    *   Frontier (early‑access)
*   **Current availability**
    *   Visible in tenant?
    *   License required?
*   **Microsoft roadmap GA estimate**
    *   Month / Quarter where available
*   **Confidence level**
    *   High (Microsoft publicly committed)
    *   Medium (rolling preview → GA)
    *   Low (Frontier / experimental)
*   **Business readiness flag**
    *   ✅ Safe to promote
    *   ⚠️ Pilot only
    *   ❌ Do not commit

The Microsoft 365 Roadmap explicitly identifies GA vs preview states and removes items once GA is reached, which becomes the authoritative input source. [\[microsoft.com\]](https://www.microsoft.com/en-us/microsoft-365/roadmap)

***

## 4. Where the Data Comes From (Important)

The solution **anchors itself to Microsoft sources only**:

*   **Microsoft 365 Roadmap** for official release phase and estimated dates [\[microsoft.com\]](https://www.microsoft.com/en-us/microsoft-365/roadmap)
*   **Microsoft Copilot release notes** for GA confirmations and rollout windows [\[learn.microsoft.com\]](https://learn.microsoft.com/en-us/microsoft-365/copilot/release-notes)
*   **Wave announcements (e.g., Wave 3)** for agentic features and staged GA timelines [\[copilotcon...ulting.com\]](https://www.copilotconsulting.com/insights/microsoft-365-copilot-wave-3-enterprise-guide-2026)
*   **Frontier and Targeted Release documentation** to explain non‑GA access paths [\[mjfnet.com\]](https://mjfnet.com/p/microsoft-365-copilot-pre-release-features-and-early-access/)

This is critical because leadership will ask*“Where did this information come from?”*


***

## 6. What This Enables Internally

Once delivered, the organisation can:

*   Answer Copilot feature questions **confidently**
*   Stop over‑promising preview or frontier features
*   Align adoption plans with **real GA timelines**
*   Decide **what to pilot** vs **what to wait for**
*   Create a future automated version tied to the roadmap API

***

## 7. How This Ties Back to the Meeting

This **perfectly aligns** with what Jeff said Paul asked for:

> “I need a set of features that are available in 365 Copilot.  
> I want to know what we have turned on, what we have turned off.”

What was *implicit* but unstated:

*   Some things are “off” because **they are not GA**
*   Some things are “missing” because **they are roadmap / Frontier**
*   Some things cannot be committed to because **GA dates are uncertain**

***