"""Roles, skills, companies and topics for management students (MBA, PGDM and similar) first.

Vantage's first audience is a student preparing for placements at a business school. This module adds
the designations those students actually apply for, the skills their interviews test, and the firms
that recruit on campus. The three sets at the bottom mark what is shown first ("popular with
management students") in pickers and lists. Everything named in them must exist; loading fails if not.
"""

# ---- new skills, by field ("GENERAL" = used across fields) ------------------------------------------

CAPABILITIES = {
    "GENERAL": """
~Strategic Planning | S | strategic planning; strategy formulation
~Hypothesis-Driven Problem Solving | S | hypothesis-driven approach; issue trees
~Client Engagement Management | S | engagement management
Entrepreneurship | S | startup building; founding a startup
Business Plan Writing | S | business plan; startup business plan
Social Impact Measurement | S | impact assessment; social return on investment
Operations Research | S | linear programming; optimisation modelling
Go-to-Market Planning | S | go-to-market plan; GTM plan
~Cross-Functional Collaboration | S | cross-functional teams
~Business Communication | S | business writing; executive communication
""",
    "consulting": """
Case Interviewing | S | case interview; case cracking; consulting case
Porter's Five Forces | S | five forces analysis; Porter five forces
SWOT Analysis | S | SWOT
BCG Growth-Share Matrix | S | BCG matrix; growth-share matrix
Market Entry Strategy | S | market entry; entry strategy
Business Modeling | S | business model design; business model canvas
Value Chain Analysis | S | value chain mapping
""",
    "marketing": """
Segmentation, Targeting and Positioning | S | STP framework; STP
Marketing Mix (4Ps) | S | marketing mix; 4Ps; seven Ps
Customer Lifetime Value | S | CLV; LTV; lifetime value
Marketing Analytics | S | marketing measurement
Brand Equity | S | brand valuation; brand health
New Product Development | S | NPD; product launch planning
Distribution Strategy | S | distribution network design; route to market
Retail Analytics | S | retail data analysis
""",
    "finance": """
Corporate Finance | S | corporate financing
Capital Budgeting | S | investment appraisal; NPV analysis
Unit Economics | S | contribution margin analysis
P&L Management | S | profit and loss ownership; P&L ownership
Startup Fundraising | S | fundraising; venture funding rounds
Venture Capital Evaluation | S | startup evaluation; investment memo
Capital Markets | S | equity capital markets; debt capital markets
Financial Planning | S | personal financial planning; wealth planning
Wealth Advisory | S | private wealth advice
Asset Allocation | S | strategic asset allocation
""",
    "sales": """
Sales Strategy | S | sales planning; sales operating model
Consultative Selling | S | consultative sales
""",
    "hr": """
Talent Management | S | talent development programme; high-potential programmes
Organizational Behavior | S | organisational behaviour; OB
Industrial Relations | S | labour relations; union negotiations
""",
    "operations": """
Operations Strategy | S | operational strategy
Process Excellence | S | operational excellence; business excellence
Retail Operations | S | store operations
Service Operations | S | service delivery operations
""",
}

# ---- new roles ---------------------------------------------------------------------------------------

ROLES = {
    "consulting": """
Associate Consultant | Junior Consultant; Consulting Analyst | Competitive Analysis; Market Sizing; Business Case Development; Excel; PowerPoint; Hypothesis-Driven Problem Solving; Communication | consulting
Senior Consultant | Consultant | Business Case Development; Stakeholder Management; Operating Model Design; Project Management; PowerPoint; Team Management | consulting; itservices
Engagement Manager | Consulting Manager | Project Management; Stakeholder Management; Team Management; Client Engagement Management; Business Case Development; Leadership | consulting
Strategy Consultant | Strategy and Operations Consultant | Porter's Five Forces; SWOT Analysis; Market Entry Strategy; Competitive Analysis; Market Sizing; Business Modeling | consulting
Chief of Staff | Chief of Staff to the CEO | Strategic Planning; Stakeholder Management; OKRs; Business Communication; Project Management; Analytical Thinking
Founder's Office Associate | Founders Office Analyst; Founder's Office Manager | Strategic Planning; Business Analysis; Excel; OKRs; Problem Solving; Business Communication | ecom; fintech; saas
BizOps Manager | Business Operations Lead | Business Analysis; Process Improvement; SQL; Excel; Stakeholder Management; OKRs | saas; ecom; fintech
Corporate Development Associate | Corp Dev Associate; Corporate Development Manager | Mergers & Acquisitions; Financial Modeling; Due Diligence; Valuation; Market Sizing; PowerPoint
General Manager | Business Unit Head; Country Manager | P&L Management; Leadership; Strategic Planning; Team Management; Stakeholder Management; Operations Strategy
Entrepreneur | Startup Founder; Co-Founder | Entrepreneurship; Business Plan Writing; Startup Fundraising; Go-to-Market Planning; Leadership; Unit Economics
Social Impact Manager | Impact Programme Manager; CSR Manager | Social Impact Measurement; Project Management; Stakeholder Management; Business Communication; Budgeting
""",
    "marketing": """
Associate Brand Manager | ABM | Brand Strategy; Consumer Insights; Marketing Mix (4Ps); Campaign ROI Analysis; Excel; Segmentation, Targeting and Positioning | fmcg; retail; ecom
Marketing Manager | Marketing Lead | Brand Strategy; Segmentation, Targeting and Positioning; Marketing Analytics; Campaign Management; Budgeting; Stakeholder Management
Consumer Insights Manager | Consumer Research Manager | Consumer Insights; Market Research; Customer Segmentation; Marketing Analytics; Statistics; Storytelling | fmcg; retail; ecom; media
New Product Development Manager | NPD Manager; Innovation Marketing Manager | New Product Development; Consumer Insights; Market Sizing; Go-to-Market Planning; Project Management | fmcg; pharma; auto
Shopper Marketing Manager | Retail Marketing Manager | Trade Marketing; Retail Analytics; Category Management; Consumer Insights; Campaign Management | retail; fmcg
Pharma Brand Manager | Marketing Manager, Pharma | Brand Strategy; Market Research; Marketing Mix (4Ps); Regulatory Compliance; Sales Forecasting | pharma; healthcare
""",
    "sales": """
Area Sales Manager | ASM; Regional Sales Executive | Distributor Management; Territory Planning; Sales Forecasting; Team Management; Trade Marketing; Excel | fmcg; retail; auto; pharma
Regional Sales Manager | Zonal Sales Manager | Sales Strategy; Team Management; Sales Forecasting; Distributor Management; P&L Management; Leadership | fmcg; auto; pharma; mfg
Sales Officer | Territory Sales Officer; Field Sales Officer | Territory Planning; Distributor Management; Negotiation; Excel; Communication | fmcg; retail
Business Development Associate | BDA; Business Development Analyst | Cold Outreach; Consultative Selling; CRM; Negotiation; Excel; Communication | saas; ecom; fintech; education
""",
    "finance": """
Investment Banking Associate | Associate, Investment Banking; IB Associate | Financial Modeling; Valuation; Mergers & Acquisitions; Capital Markets; Excel; PowerPoint; Due Diligence | capmkts; banking
Equity Research Associate | Research Associate | Equity Research; Financial Modeling; Valuation; Financial Statement Analysis; Bloomberg Terminal; Excel | capmkts; assetmgmt
Investment Analyst | Investment Associate | Investment Analysis; Financial Modeling; Valuation; Due Diligence; Excel; Portfolio Management | assetmgmt; capmkts
Venture Capital Associate | VC Associate | Venture Capital Evaluation; Market Sizing; Due Diligence; Financial Modeling; Startup Fundraising; Unit Economics | assetmgmt; fintech; saas
Credit Manager | Credit Appraisal Manager | Credit Analysis; Financial Statement Analysis; Risk Management; Working Capital Management; Excel | banking; fintech
Financial Planner | Financial Planning Advisor; Wealth Planner | Financial Planning; Asset Allocation; Portfolio Management; Wealth Advisory; Communication | banking; assetmgmt; insurance
Commercial Finance Manager | Business Finance Manager | P&L Management; Budgeting; FP&A; Financial Modeling; Excel; Stakeholder Management | fmcg; mfg; retail; saas
Corporate Banking Relationship Manager | Corporate Banking Manager | Credit Analysis; Financial Statement Analysis; Key Account Management; Negotiation; Working Capital Management | banking
Retail Banking Manager | Branch Manager | Team Management; Sales Strategy; Regulatory Compliance; P&L Management; Communication | banking
""",
    "hr": """
HR Generalist | HR Executive; HR Manager | Employee Engagement; Employee Relations; Performance Management; HRIS; Labor Law; Talent Acquisition
Talent Management Manager | Talent Development Manager | Talent Management; Succession Planning; Performance Management; Learning and Development; People Analytics; Organizational Behavior
Industrial Relations Manager | Labour Relations Manager | Industrial Relations; Labor Law; Employee Relations; Negotiation; Stakeholder Management | mfg; auto; energy
""",
    "operations": """
Supply Chain Manager | SCM Manager | Supply Chain Planning; Demand Forecasting; Inventory Management; Logistics Optimization; S&OP; Stakeholder Management
Operations Excellence Manager | Operational Excellence Lead | Six Sigma; Lean Manufacturing; Process Improvement; Operations Strategy; Root Cause Analysis; Kaizen | mfg; auto; logistics
Retail Operations Manager | Store Operations Manager | Retail Operations; Inventory Management; Team Management; P&L Management; Process Improvement | retail; ecom
E-commerce Category Manager | Online Category Manager | Category Management; Pricing Strategy; Strategic Sourcing; Excel; SQL; Retail Analytics | ecom; retail
Operations Research Analyst | OR Analyst | Operations Research; Python; Excel; Statistics; Capacity Planning | logistics; mfg; transport
""",
    "data-ai": """
Analytics Manager | Business Analytics Manager | Marketing Analytics; SQL; Tableau; Statistics; Storytelling; Stakeholder Management
""",
    "healthcare": """
Hospital Administrator | Hospital Operations Manager | Operations Strategy; Budgeting; Regulatory Compliance; Team Management; Process Improvement; Stakeholder Management | healthcare
Healthcare Management Consultant | Healthcare Strategy Consultant | Market Sizing; Competitive Analysis; Regulatory Compliance; Business Case Development; PowerPoint; Stakeholder Management | consulting; healthcare; pharma
""",
}

TOPICS = {
    "finance": """
""",
    "marketing": """
Consumer Demand Trends | rural demand; urban demand; consumption slowdown
Brand Launches | brand launch; relaunch of the brand
""",
    "hr": """
Management Trainee Programmes | management trainee; graduate trainee programme; MT programme
""",
    "consulting": """
Leadership Changes | appoints CEO; new CEO; CEO steps down; CFO resigns; leadership reshuffle
Corporate Restructuring | demerger; spin-off; corporate restructuring; business separation
""",
}

# ---- companies that recruit at business schools, or that management graduates aim for ----------------

COMPANIES = """
Kearney | consulting | A.T. Kearney
Oliver Wyman | consulting
L.E.K. Consulting | consulting | LEK Consulting
Roland Berger | consulting
Arthur D. Little | consulting
Alvarez & Marsal | consulting
ZS Associates | consulting | ZS
Strategy& | consulting
RedSeer Consulting | consulting | RedSeer
Gartner | consulting
NielsenIQ | consulting | Nielsen
Kantar | consulting
Ipsos | consulting
IQVIA | pharma
Fractal Analytics | itservices
Mu Sigma | itservices
Tiger Analytics | itservices
EXL Service | itservices | EXL
Genpact | itservices
WNS Global Services | itservices | WNS
Cushman & Wakefield | realestate
Colliers | realestate
Knight Frank | realestate
IDFC First Bank | banking
Yes Bank | banking
IndusInd Bank | banking
Federal Bank | banking
Shriram Finance | banking
Muthoot Finance | banking
Aditya Birla Capital | banking
Tata Capital | banking
SBI Life Insurance | insurance
Max Life Insurance | insurance
Tata AIA Life Insurance | insurance | Tata AIA
ICICI Lombard | insurance
Star Health Insurance | insurance
Acko | insurance | Acko General Insurance
PolicyBazaar | fintech
Kotak Securities | capmkts
ICICI Securities | capmkts
Edelweiss | capmkts | Edelweiss Financial Services
Motilal Oswal | capmkts
Avendus Capital | capmkts | Avendus
JM Financial | capmkts
Jefferies | capmkts
Credit Suisse | capmkts
Bain Capital | assetmgmt
Peak XV Partners | assetmgmt | Sequoia Capital India | avoid:sequoia national park
Accel | assetmgmt | Accel Partners
Tiger Global | assetmgmt
Nexus Venture Partners | assetmgmt
Kalaari Capital | assetmgmt
HDFC Asset Management | assetmgmt | HDFC AMC
Mirae Asset | assetmgmt
Nippon India Mutual Fund | assetmgmt
Aditya Birla Group | holding | Aditya Birla
Tata Sons | holding | Tata Group
Godrej Industries | fmcg
Honasa Consumer | fmcg | Mamaearth
Sugar Cosmetics | fmcg
boAt Lifestyle | fmcg | boAt
Patanjali Ayurved | fmcg | Patanjali
Wipro Consumer Care | fmcg
Jyothy Labs | fmcg
Bajaj Consumer Care | fmcg
Haldiram's | fmcg | Haldirams
Parle Products | fmcg
Kellogg's | fmcg | Kellogg
Ferrero | fmcg
Kimberly-Clark | fmcg
Beiersdorf | fmcg | Nivea
Estee Lauder | fmcg
United Spirits | fmcg
Diageo | fmcg
Pernod Ricard | fmcg
AB InBev | fmcg | Anheuser-Busch InBev
Carlsberg | fmcg
Heineken | fmcg
Raymond | retail | | avoid:Raymond Chandler
Trent | retail | Westside | avoid:Trent Alexander-Arnold; avoid:River Trent
Aditya Birla Fashion and Retail | retail | ABFRL
Shoppers Stop | retail
Future Group | retail
Spencer's Retail | retail
Lenskart | retail
FirstCry | ecom
Licious | ecom
Zepto | ecom
Blinkit | ecom
Tata CLiQ | ecom
Spinny | ecom
Cars24 | ecom
CarDekho | ecom
Practo | healthcare
PharmEasy | ecom
Dream Sports | media | Dream11
ShareChat | media
Sony | mfg | | avoid:Sony Music; avoid:Sony Pictures
Samsung | mfg
LG Electronics | mfg | LG
Whirlpool | mfg
Philips | mfg
Voltas | mfg
Blue Star | mfg
Daikin | mfg
Crompton Greaves Consumer Electricals | mfg | Crompton
Godrej & Boyce | mfg
Schneider Electric | mfg
Honeywell | mfg
General Electric | mfg | GE
Cummins | mfg
Caterpillar | mfg
Mercedes-Benz | auto
BMW | auto
Volkswagen | auto
Hyundai | auto
Kia | auto
Honda | auto
TVS Motor | auto
Eicher Motors | auto | Royal Enfield
Ola Electric | auto
Ather Energy | auto
Hindustan Petroleum | energy | HPCL
Bharat Petroleum | energy | BPCL
Shell | energy | | avoid:shell company; avoid:shell script; avoid:shell companies; avoid:seashell; avoid:eggshell
TotalEnergies | energy
Adani Green Energy | energy
ReNew | energy | ReNew Power
Torrent Power | utilities
Lupin | pharma
Zydus Lifesciences | pharma | Zydus
Mankind Pharma | pharma
Abbott | pharma | | avoid:Abbott Elementary
Novartis | pharma
GSK | pharma | GlaxoSmithKline
Sanofi | pharma
AstraZeneca | pharma
Roche | pharma
Medtronic | healthcare
Manipal Hospitals | healthcare
Aster DM Healthcare | healthcare
Berger Paints | materials
Kansai Nerolac | materials
Ambuja Cements | materials
Shree Cement | materials
Grasim | materials
Eruditus | education
Great Learning | education
PhysicsWallah | education
Vedantu | education
LinkedIn | saas
Ecom Express | logistics
Shadowfax | logistics
"""

# ---- what is shown first for management students -----------------------------------------------------

MBA_ROLES = {
    # marketing
    "Brand Manager", "Associate Brand Manager", "Marketing Manager", "Digital Marketing Manager", "Marketing Analyst",
    "Product Marketing Manager", "Growth Marketing Manager", "Category Manager", "Trade Marketing Manager",
    "Consumer Insights Manager", "New Product Development Manager", "Shopper Marketing Manager", "Pharma Brand Manager",
    "Market Research Analyst", "Performance Marketing Manager", "Revenue Growth Management Analyst",
    # finance
    "Financial Analyst", "Investment Banking Analyst", "Investment Banking Associate", "Equity Research Analyst",
    "Equity Research Associate", "Investment Analyst", "Venture Capital Analyst", "Venture Capital Associate",
    "Private Equity Associate", "M&A Analyst", "Credit Analyst", "Credit Manager", "Risk Analyst", "Treasury Analyst",
    "FP&A Manager", "Corporate Finance Manager", "Commercial Finance Manager", "Portfolio Manager",
    "Wealth Management Advisor", "Financial Planner", "Relationship Manager (Banking)", "Corporate Banking Relationship Manager",
    "Retail Banking Manager", "Investor Relations Manager", "ESG Analyst",
    # consulting and strategy
    "Management Consultant", "Associate Consultant", "Senior Consultant", "Engagement Manager", "Strategy Consultant",
    "Strategy Analyst", "Corporate Strategy Manager", "Corporate Development Associate", "Business Analyst",
    "Operations Consultant", "Transformation Manager", "Program Manager", "Project Manager", "Management Trainee",
    "Innovation Manager", "Chief of Staff", "Founder's Office Associate", "BizOps Manager", "General Manager",
    "Entrepreneur", "Social Impact Manager", "Healthcare Management Consultant", "Hospital Administrator",
    # sales, hr, operations, product, analytics
    "Business Development Manager", "Business Development Associate", "Key Account Manager", "Area Sales Manager",
    "Regional Sales Manager", "Sales Officer", "Territory Sales Manager", "Account Executive", "Enterprise Account Manager",
    "B2B Marketing Manager", "HR Business Partner", "HR Generalist", "Talent Acquisition Specialist", "Campus Recruiter",
    "Talent Management Manager", "Learning and Development Manager", "People Analytics Analyst", "Industrial Relations Manager",
    "Operations Manager", "Supply Chain Manager", "Supply Chain Analyst", "Demand Planner", "Procurement Manager",
    "Logistics Manager", "S&OP Manager", "Operations Excellence Manager", "Retail Operations Manager",
    "E-commerce Category Manager", "Operations Research Analyst", "Product Manager", "Associate Product Manager",
    "Fintech Product Manager", "Analytics Manager", "Digital Transformation Manager", "Platform Product Manager",
    "Pricing Analyst", "Due Diligence Analyst", "Post-Merger Integration Manager", "Sales Operations Analyst",
    "Communications & PR Manager", "Compensation and Benefits Analyst", "Workforce Planning Analyst",
    "Organizational Development Consultant", "Product Operations Manager",
}

MBA_SKILLS = {
    "Excel", "PowerPoint", "SQL", "Power BI", "Tableau", "Financial Modeling", "Valuation", "Discounted Cash Flow",
    "Market Sizing", "Business Case Development", "Competitive Analysis", "Case Interviewing", "Porter's Five Forces",
    "SWOT Analysis", "BCG Growth-Share Matrix", "Market Entry Strategy", "Business Modeling", "Strategic Planning",
    "Brand Strategy", "Consumer Insights", "Segmentation, Targeting and Positioning",
    "Marketing Mix (4Ps)", "Customer Lifetime Value", "Category Management", "Trade Marketing", "Performance Marketing",
    "Marketing Analytics", "New Product Development", "Go-to-Market Strategy", "Go-to-Market Planning", "Pricing Strategy",
    "Unit Economics", "P&L Management", "Corporate Finance", "Capital Budgeting", "Mergers & Acquisitions", "Due Diligence",
    "Equity Research", "Portfolio Management", "Credit Analysis", "Startup Fundraising", "Venture Capital Evaluation",
    "Entrepreneurship", "Supply Chain Planning", "Demand Forecasting", "S&OP", "Six Sigma", "Operations Strategy",
    "Process Excellence", "Talent Acquisition", "Talent Management", "Organizational Behavior", "Employee Engagement",
    "Key Account Management", "Sales Strategy", "Sales Forecasting", "Consultative Selling", "Product Roadmapping",
    "Design Thinking", "OKRs", "Agile", "Change Management", "Communication", "Leadership", "Negotiation",
    "Presentation Skills", "Problem Solving", "Analytical Thinking", "Team Management", "Stakeholder Management",
    "Project Management", "Business Analysis", "Hypothesis-Driven Problem Solving",
}

MBA_COMPANIES = {
    # FMCG and consumer
    "Hindustan Unilever", "ITC", "Nestle India", "Procter & Gamble", "Colgate-Palmolive", "Dabur", "Britannia", "Marico",
    "Godrej Consumer Products", "Coca-Cola", "PepsiCo", "Mondelez", "Tata Consumer Products", "Reckitt", "L'Oreal",
    "Asian Paints", "Titan Company", "Honasa Consumer", "Diageo", "Pernod Ricard", "Kellogg's", "Ferrero", "Kimberly-Clark",
    "Estee Lauder", "Patanjali Ayurved", "United Spirits",
    # consulting and analytics
    "McKinsey & Company", "Boston Consulting Group", "Bain & Company", "Deloitte", "PwC", "EY", "KPMG", "Accenture",
    "Kearney", "Oliver Wyman", "L.E.K. Consulting", "ZS Associates", "Strategy&", "Alvarez & Marsal", "Gartner", "NielsenIQ",
    "Kantar", "Fractal Analytics", "Mu Sigma", "Genpact", "EXL Service", "Capgemini", "IBM",
    # banking, finance, investing
    "HDFC Bank", "ICICI Bank", "State Bank of India", "Axis Bank", "Kotak Mahindra Bank", "IDFC First Bank", "Yes Bank",
    "IndusInd Bank", "Bajaj Finserv", "Aditya Birla Capital", "Tata Capital", "JPMorgan Chase", "Citigroup",
    "HSBC", "Standard Chartered", "Deutsche Bank", "Barclays", "Bank of America", "Goldman Sachs", "Morgan Stanley", "Nomura",
    "Jefferies", "Kotak Securities", "ICICI Securities", "Edelweiss", "Motilal Oswal", "Avendus Capital", "JM Financial",
    "BlackRock", "Blackstone", "KKR", "Bain Capital", "Peak XV Partners", "Accel", "Nexus Venture Partners",
    "HDFC Asset Management", "HDFC Life", "SBI Life Insurance", "Max Life Insurance", "ICICI Lombard", "Paytm", "PhonePe",
    "Razorpay", "CRED", "PolicyBazaar",
    # technology and platforms
    "Amazon India", "Flipkart", "Myntra", "Nykaa", "Zomato", "Swiggy", "Google", "Microsoft", "Meta Platforms", "Adobe",
    "Salesforce", "Oracle", "SAP SE", "Tata Consultancy Services", "Infosys", "Wipro", "HCLTech", "LinkedIn", "Zepto",
    "Blinkit", "Lenskart", "Cars24", "Meesho", "Urban Company", "Byju's", "upGrad", "Eruditus",
    # industrial, auto, pharma, energy, conglomerates
    "Tata Sons", "Aditya Birla Group", "Reliance Industries", "Reliance Retail", "Reliance Jio", "Bharti Airtel",
    "Mahindra & Mahindra", "Tata Motors", "Maruti Suzuki", "Hero MotoCorp", "Bajaj Auto", "Larsen & Toubro", "Siemens",
    "ABB", "Bosch", "Tata Steel", "Sun Pharma", "Dr. Reddy's", "Cipla", "Apollo Hospitals", "UPL", "Pidilite",
    "Hindustan Petroleum", "Bharat Petroleum", "Trent", "Aditya Birla Fashion and Retail", "Shoppers Stop", "DMart",
}
