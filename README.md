<img width="1584" height="396" alt="linkedin-1584x396" src="https://github.com/user-attachments/assets/397f9611-3817-4a77-ac1d-9582baa7e33a" />

# 👋 Hey, I’m Cabuco

<sub>*This README was AI-assisted. Human-approved. Slightly overthought.*</sub>

Senior IT Support Specialist by title.  
In practice, I’m very much a **Guy in the Chair**.

I sit just off-screen, watching dashboards, logs, and timelines — feeding the right information at the right moment so things don’t blow up (or so they blow up *less*).

---

## 🧠 What I Do
- Support complex enterprise environments (Google Workspace, Microsoft 365, Okta, Slack, Zoom, etc.)
- Untangle cross-platform issues that only show up when everything is “configured correctly”
- Anticipate failure modes before they become incidents
- Translate between IT, Legal, Security, and end users so everyone can keep moving

If you’re in the field trying to save the day, I’m probably in the background saying  
“Okay, pause — here’s what’s actually happening.”

---

## 🛠️ My Toolkit (and Why It Matters)
- Identity & Access (SSO, provisioning, migrations, edge cases no one documented)
- Email & calendar migrations (including explaining why *sync* is not a promise)
- Google Workspace administration (custom schemas, GAM, audits, forensic visibility)
- Asset lifecycle & logistics (deployment → replacement → legal hold → international return)
- Incident response that favors calm, clarity, and decisive info

I don’t swing the hammer unless it’s needed.  
I make sure the person who does has the right target.

---

## 🧰 Featured Automations & Tools

To eliminate repetitive manual tasks, accelerate cross-platform audits, and streamline IT operations, I build and maintain custom cloud-hosted tools. Each runs inside its own isolated GitHub Codespace container.

### ⚡ [Entra Vs. Okta Suite (EvO)](./ai-scripts/EvO)
An enterprise IT automation utility built with Python and Streamlit to audit identity drift, automate deprovisioning workflows, and translate directory objects between Okta and Microsoft Entra ID.

* **📋 Primary Identity Mapper:** Bidirectional mapping between platform email handles (`@github.com`) and corporate Microsoft Object IDs (`@microsoft.com`).
* **🔄 Group Reconciliation Engine:** Audits Okta auto-distribution groups against manual Entra ID groups and outputs bulk `memberObjectIdOrUpn` CSVs for additions and removals in Azure.
* **🪪 External Identity Resolver:** Converts vendor and guest contractor email addresses into Azure `#EXT#` UPNs and resolves cloud Object IDs.
* **📊 Account Status Checker:** Bulk-checks employee employment status (`ACTIVE`, `SUSPENDED`, `DEACTIVATED`) against directory master records.
* **🌐 Group Roster API Fetcher:** Streams live security and distribution group rosters on demand via the Okta SSWS API.
* **🤖 The Terminator:** Offboarding hardware retrieval engine that checks user devices against Okta API and auto-generates chunked Zendesk search queries (`ticket_id:"<ID>"`) for bulk ticket closure and ABM MacBook verification.

👉 [View EvO Documentation & Usage Guide](./ai-scripts/EvO/README.md)

---

### 📜 [Rosetta — Slack Export PDF Converter](./ai-scripts/slack/rosetta)
Decodes official, unstructured Slack export `.zip` archives and converts them into clean, human-readable PDF reports for Legal, HR, and compliance investigations.

* **Identity Resolution:** Maps raw Slack user IDs, channel IDs, and DMs to display names.
* **Streaming Processing:** Handles multi-gigabyte Slack exports without crashing by streaming conversations into split PDF reports.
* **Privacy-First:** Processes archives entirely inside an isolated Codespace container with zero external data transfer.

👉 [View Rosetta Documentation & Usage Guide](./ai-scripts/slack/rosetta/README.md)

---

## 🧩 What I Optimize For
- Signal over noise
- Boring reliability
- Clear ownership and sane defaults
- Systems that fail *predictably*, not creatively
- Humans not being punished by the tools meant to help them

---

## 🚫 Things I’m Not Trying to Be
- A full-time scripter (automation is a tool, not my personality)
- The loudest voice in the room

---

## 🎮 When I’m Not in the Chair
- Disney and the MCU (Spider-Man especially — obviously)
- K-pop (ILLIT has permanent brain residency)
- Over-researching menus before ordering
- Optimizing credit card benefits like it’s a mini-game
- Asking “wait… why?” until the root cause gives up

---

## 📍 Current Status
Operating in environments that are “mostly fine” until they need someone behind the scenes.

---

## 🧾 Operating Principle
> The best heroes aren’t always visible.  
> Sometimes they’re the reason the mission works at all.
> Never say, "I don't know." Always say, "I'll find out."

If you value preparation, clear comms, and systems that don’t panic — we’ll get along.
