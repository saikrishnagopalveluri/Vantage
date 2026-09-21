"""More consulting, advisory, technology-services and digital-transformation companies and roles.

Added because the first lists covered the big names but missed most of the firms a management student
actually meets: the mid-tier accounting and advisory firms, boutique strategy houses, HR and talent
consultancies, research firms, IT services companies and the platforms that digital-transformation
programmes are built on. Merged into the management-student lists at the bottom of `mba.py`.

Format is the same as the other modules: `Name | industry | aliases | avoid:phrase`. A name that is also
an ordinary word or another company's name carries `avoid:` phrases so it is not tagged by mistake.
"""

COMPANIES = """
# Accounting, audit and advisory firms
Grant Thornton | consulting | Grant Thornton Bharat; Grant Thornton Advisors
BDO | consulting | BDO India; BDO International
RSM | consulting | RSM International; RSM US | avoid:RSM Motors
Forvis Mazars | consulting | Mazars
Crowe | consulting | Crowe LLP; Crowe Horwath | avoid:Russell Crowe
Baker Tilly | consulting
Protiviti | consulting
Guidehouse | consulting
Booz Allen Hamilton | consulting | Booz Allen
ICF | consulting | ICF International
West Monroe | consulting
Slalom | consulting | Slalom Consulting | avoid:slalom skiing; avoid:slalom course; avoid:slalom race
Sia Partners | consulting
Wavestone | consulting
# Strategy, restructuring and economic consulting
Simon-Kucher & Partners | consulting | Simon-Kucher
AlixPartners | consulting
FTI Consulting | consulting | FTI
Huron Consulting | consulting | Huron Consulting Group | avoid:Lake Huron; avoid:Huron County
Bridgespan Group | consulting | The Bridgespan Group
Dalberg Advisors | consulting | Dalberg
Charles River Associates | consulting | CRA International
Analysis Group | consulting
Cornerstone Research | consulting
Argon & Co | consulting | Argon and Co
Efficio | consulting
Palladium | consulting | Palladium International
Avalon Consulting | consulting | Avalon Consulting India
Monitor Deloitte | consulting
EY-Parthenon | consulting | EY Parthenon
BCG X | consulting | BCG Gamma
QuantumBlack | consulting | QuantumBlack AI by McKinsey
Bain Capability Network | consulting | Bain Capability Center
# HR, talent and risk consultancies
Mercer | consulting | Mercer HR | avoid:Mercer County; avoid:Mercer Island
Aon | consulting | Aon plc
WTW | consulting | Willis Towers Watson; Towers Watson
Marsh McLennan | consulting | Marsh & McLennan
Korn Ferry | consulting | Hay Group
Heidrick & Struggles | consulting | Heidrick
Spencer Stuart | consulting
Egon Zehnder | consulting
Russell Reynolds Associates | consulting | Russell Reynolds
# Research and advisory
Zinnov | consulting | Zinnov Management Consulting
Everest Group | consulting
ISG | consulting | Information Services Group
HFS Research | consulting
IDC | consulting | International Data Corporation
Frost & Sullivan | consulting
Forrester | consulting | Forrester Research
Euromonitor International | consulting | Euromonitor
Mintel | consulting
GfK | consulting
YouGov | consulting
Counterpoint Research | consulting
Gallup | consulting
# IT services and digital engineering
Mphasis | itservices
Persistent Systems | itservices | Persistent
Coforge | itservices | NIIT Technologies
Hexaware Technologies | itservices | Hexaware
Cyient | itservices
Birlasoft | itservices
Zensar Technologies | itservices | Zensar
Sonata Software | itservices
KPIT Technologies | itservices | KPIT
Tata Elxsi | itservices
Happiest Minds | itservices | Happiest Minds Technologies
Mastek | itservices
Virtusa | itservices
EPAM Systems | itservices | EPAM
Globant | itservices
Endava | itservices
Thoughtworks | itservices | ThoughtWorks
Publicis Sapient | itservices | Sapient
DXC Technology | itservices | DXC
Kyndryl | itservices
Atos | itservices | Eviden
NTT DATA | itservices
Fujitsu | itservices
Unisys | itservices
CGI | itservices | CGI Group
Sopra Steria | itservices
Nagarro | itservices
Concentrix | itservices
Teleperformance | itservices
TaskUs | itservices
Deloitte Digital | itservices
Accenture Song | itservices
# Platforms, automation and cloud that digital transformation is built on
Workday | saas | avoid:Workday of
OpenText | saas | Open Text
HubSpot | saas
Twilio | saas
Okta | saas
CrowdStrike | saas
Palo Alto Networks | saas
Zscaler | saas
Cloudflare | saas
Datadog | saas
MongoDB | saas
Elastic | saas | Elasticsearch company
Confluent | saas
GitLab | saas
Cisco | saas | Cisco Systems
Dell Technologies | saas | Dell
Hewlett Packard Enterprise | saas | HPE
Red Hat | saas
Autodesk | saas
# Indian technology companies and startups
Postman | saas | | avoid:Postman Pat
BrowserStack | saas
Chargebee | saas
Ola | ecom | Ola Cabs; ANI Technologies | avoid:Ola Kala
InMobi | media
Info Edge | media | Naukri; Naukri.com
Tally Solutions | saas | Tally Prime
"""

CAPABILITIES = {
    "consulting": """
~Proposal Writing | S | bid writing; proposal development; RFP response writing
~Solution Architecture | S | solution design; technical solution design
Forensic Accounting | S | forensic investigation; fraud investigation
Audit and Assurance | S | assurance services
Transaction Advisory | S | deal advisory; transaction services; financial due diligence
Restructuring | S | corporate restructuring; turnaround
Generative AI Strategy | S | enterprise AI strategy; AI adoption strategy
Data Strategy | S | data and analytics strategy
Cloud Strategy | S | cloud transformation strategy
Customer Experience Strategy | S | CX strategy; customer experience transformation
""",
}

# title | aliases | skills (all must exist) | industries the role is limited to (optional)
ROLES = {
    "consulting": """
Principal | Consulting Principal; Principal Consultant | Client Engagement Management; Team Management; Proposal Writing; Business Case Development; Leadership; Stakeholder Management | consulting
Associate Partner | Junior Partner | Client Engagement Management; Proposal Writing; Leadership; Stakeholder Management; P&L Management; Strategic Planning | consulting
Partner | Consulting Partner; Managing Director (Consulting) | Client Engagement Management; Proposal Writing; Leadership; P&L Management; Strategic Planning; Negotiation | consulting
Case Team Leader | Team Lead (Consulting) | Team Management; Hypothesis-Driven Problem Solving; Client Engagement Management; PowerPoint; Project Management | consulting
Consulting Director | Practice Director | Client Engagement Management; Leadership; P&L Management; Proposal Writing; Stakeholder Management | consulting
Practice Lead | Consulting Practice Lead; Capability Lead | Leadership; Client Engagement Management; Proposal Writing; Strategic Planning; Team Management | consulting
Digital Transformation Consultant | Digital Transformation Advisor | Digital Strategy; Business Transformation; Change Management; Agile; Stakeholder Management; Business Process Design; PowerPoint | consulting; itservices
Technology Strategy Consultant | IT Strategy Consultant | Enterprise Architecture; Digital Strategy; Cloud Strategy; Business Case Development; Stakeholder Management; PowerPoint | consulting; itservices
Cloud Transformation Consultant | Cloud Consultant | Cloud Strategy; Cloud Migration; AWS; Microsoft Azure; Google Cloud Platform; Business Case Development; Stakeholder Management | consulting; itservices
Data and Analytics Consultant | Analytics Consultant | Data Strategy; Data Analysis; SQL; Power BI; Tableau; Python; Stakeholder Management; PowerPoint | consulting; itservices
AI Strategy Consultant | Generative AI Consultant; AI Consultant | Generative AI Strategy; Data Strategy; Business Case Development; Stakeholder Management; PowerPoint; AI Governance | consulting; itservices
Salesforce Consultant | Salesforce Functional Consultant | Salesforce CRM; CRM; Requirements Gathering; Business Process Design; Stakeholder Management | consulting; itservices
Risk Consultant | Risk Advisory Consultant | Risk Management; Regulatory Compliance; Internal Audit; Stakeholder Management; Excel; PowerPoint | consulting
Financial Advisory Analyst | Deal Advisory Analyst; Transaction Services Analyst | Transaction Advisory; Due Diligence; Financial Modeling; Financial Statement Analysis; Excel; PowerPoint | consulting
Forensic Consultant | Forensic Accountant; Forensic Analyst | Forensic Accounting; Digital Forensics; Due Diligence; Data Analysis; Excel; Regulatory Compliance | consulting
Restructuring Consultant | Turnaround Consultant | Restructuring; Financial Modeling; Cost Optimization; Stakeholder Management; PowerPoint; Excel | consulting
Human Capital Consultant | HR Consultant; People Advisory Consultant | Organizational Development; Change Management; Compensation Benchmarking; Talent Management; Stakeholder Management; PowerPoint | consulting
Customer Experience Consultant | CX Consultant; CX Strategy Consultant | Customer Experience Strategy; Journey Mapping; Digital Customer Experience; Customer Segmentation; Stakeholder Management | consulting
Supply Chain Strategy Consultant | Supply Chain Transformation Consultant | Supply Chain Planning; Supply Chain Digitisation; Operations Strategy; Cost Optimization; Excel; PowerPoint | consulting
Marketing Transformation Consultant | Marketing Strategy Consultant | Marketing Analytics; Marketing Automation; Digital Strategy; Customer Segmentation; Stakeholder Management; PowerPoint | consulting
Change Management Consultant | Organizational Change Consultant | Change Management; Change Adoption; Stakeholder Management; Communication; Organisational Readiness; PowerPoint | consulting
PMO Lead | PMO Manager; Transformation Office Lead | PMO; Project Management; Stakeholder Management; Benefits Realization; Agile; Leadership | consulting
Delivery Manager | Engagement Delivery Manager; Service Delivery Manager | Project Management; Agile; Stakeholder Management; Client Relationship Management; Team Management; Risk Management | consulting; itservices
Client Partner | Client Relationship Partner; Client Director | Client Relationship Management; Account Planning; Enterprise Sales; Stakeholder Management; P&L Management; Negotiation | consulting; itservices
Presales Consultant | Presales Manager; Solution Consultant | Proposal Writing; Solution Architecture; Product Demos; RFP Management; Presentation Skills; Stakeholder Management | itservices; consulting; saas
Research Analyst (Consulting) | Knowledge Analyst; Insights Analyst; Industry Analyst | Market Research; Competitive Analysis; Data Analysis; Excel; PowerPoint; Business Communication | consulting
Management Analyst | Management Consultant Analyst | Business Analysis; Data Analysis; Excel; PowerPoint; Problem Solving; Business Communication | consulting
""",
    "digital-transformation": """
Automation Lead | Intelligent Automation Lead; RPA Lead | Robotic Process Automation; Process Automation; UiPath; Process Mining; Business Process Design; Stakeholder Management
Innovation Lead | Head of Innovation; Digital Innovation Manager | Digital Innovation; Design Thinking; Stakeholder Management; Business Case Development; Prototyping; Leadership
""",
    "it-security": """
Technical Program Manager | TPM | TPM; Project Management; Agile; Stakeholder Management; System Design; Risk Management
""",
    "sales": """
Solutions Consultant | Sales Engineer (Solutions) | Pre-Sales Engineering; Product Demos; Solution Selling; RFP Management; Presentation Skills; Stakeholder Management | saas; itservices
Implementation Consultant | Customer Implementation Manager; Onboarding Consultant | Customer Onboarding; Project Management; Requirements Gathering; Stakeholder Management; Business Process Design; SaaS Sales
Technical Account Manager | TAM | Client Relationship Management; Customer Success; Troubleshooting; Stakeholder Management; Account Planning | saas; itservices
Customer Success Consultant | Strategic Customer Success Manager | Customer Success; Client Relationship Management; Account Planning; Gainsight; Stakeholder Management | saas
""",
}

# Shown first to management students in pickers and lists (see MBA_ROLES and MBA_COMPANIES in mba.py).
MBA_COMPANIES = {
    "Grant Thornton", "BDO", "RSM", "Forvis Mazars", "Protiviti", "Guidehouse", "Booz Allen Hamilton", "Slalom",
    "Simon-Kucher & Partners", "AlixPartners", "FTI Consulting", "Huron Consulting", "Bridgespan Group", "Dalberg Advisors",
    "Monitor Deloitte", "EY-Parthenon", "BCG X", "QuantumBlack", "Bain Capability Network", "Avalon Consulting",
    "Mercer", "Aon", "WTW", "Marsh McLennan", "Korn Ferry", "Heidrick & Struggles", "Spencer Stuart", "Egon Zehnder",
    "Zinnov", "Everest Group", "ISG", "IDC", "Frost & Sullivan", "Euromonitor International",
    "Cognizant", "LTIMindtree", "Mphasis", "Persistent Systems", "Coforge", "Thoughtworks", "Publicis Sapient", "Tech Mahindra",
    "Deloitte Digital", "Accenture Song", "NTT DATA", "CGI", "ServiceNow", "Workday", "Databricks", "Palantir",
    "UiPath", "Anthropic", "OpenAI", "Nvidia", "Zoho", "Freshworks", "HubSpot", "Groww", "Zerodha", "upGrad", "Info Edge",
}

MBA_ROLES = {
    "Principal", "Associate Partner", "Partner", "Case Team Leader", "Digital Transformation Consultant",
    "Technology Strategy Consultant", "Data and Analytics Consultant", "AI Strategy Consultant",
    "Risk Consultant", "Financial Advisory Analyst", "Human Capital Consultant", "Customer Experience Consultant",
    "Supply Chain Strategy Consultant", "Marketing Transformation Consultant", "Change Management Consultant",
    "Presales Consultant", "Research Analyst (Consulting)", "Management Analyst", "Technical Program Manager", "Solutions Consultant",
    "Implementation Consultant", "Customer Success Consultant",
}

MBA_SKILLS = {
    "Proposal Writing", "Generative AI Strategy", "Data Strategy", "Cloud Strategy", "Customer Experience Strategy",
    "Transaction Advisory", "Restructuring",
}
