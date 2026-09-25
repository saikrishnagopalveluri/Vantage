"""Labelled headlines for measuring tagging accuracy against the real taxonomy.

Each case: (title, teaser, expected) where expected maps a tag kind to the entity names that
SHOULD be tagged. Industries are derived from companies, so they are not asserted. Anything
tagged that is not listed counts as a false positive, so every case also guards precision.
"""

C, K, T, R = "company", "capability", "topic", "role"


def case(title, teaser="", **expected):
    return title, teaser, {kind: set(names) for kind, names in expected.items()}


# --- Should tag ---------------------------------------------------------------------------------
POSITIVE = [
    case("HUL reports quarterly results as rural volumes recover", company=["Hindustan Unilever"], topic=["Corporate Earnings"]),
    case("Nestlé India cuts prices on Maggi packs", company=["Nestle India"]),
    case("ITC expands its hotels business after demerger", company=["ITC"]),
    case("Procter & Gamble bets on retail media networks", company=["Procter & Gamble"], topic=["Retail Media Networks"], capability=["Retail Media"]),
    case("Flipkart and Meesho race in quick commerce", company=["Flipkart", "Meesho"], topic=["Quick Commerce"]),
    case("Swiggy files for IPO to raise funds", company=["Swiggy"], topic=["Initial Public Offerings"]),
    case("Zomato's new feature lifts app downloads", company=["Zomato"], topic=["Consumer Apps"]),
    case("Google Analytics 4 adds new attribution reports", company=["Google"], capability=["Google Analytics"]),
    case("Meta Ads Manager changes how campaigns report ROAS", company=["Meta Platforms"], capability=["Meta Ads", "Campaign ROI Analysis"]),
    case("Semrush and Ahrefs both add AI overviews tracking", capability=["Semrush", "Ahrefs"]),
    case("Why SEO teams are rethinking content strategy", capability=["SEO", "Content Strategy"]),
    case("Influencer marketing spend tops $30 billion", capability=["Influencer Marketing"]),
    case("Third-party cookies finally fade as ad privacy rules tighten", topic=["Privacy and Cookies"]),
    case("RBI cuts repo rate by 25 basis points", topic=["Central Banks", "Interest Rates"]),
    case("Sensex and Nifty close higher as banks rally", topic=["Stock Markets"]),
    case("HDFC Bank reports fall in NPAs", company=["HDFC Bank"], topic=["Banking Sector"]),
    case("Goldman Sachs analysts turn to Python for financial modeling", company=["Goldman Sachs"], capability=["Python", "Financial Modeling"]),
    case("Razorpay raises Series B round", company=["Razorpay"], topic=["Venture Capital and Private Equity"]),
    case("SEBI tightens rules for mutual funds", topic=["Financial Regulation"]),
    case("Bitcoin slides as stablecoin rules loom", topic=["Cryptocurrency"]),
    case("GST council meets to review rates", topic=["Taxation and GST"]),
    case("Basel III endgame rules spark bank pushback", capability=["Basel III"]),
    case("Kubernetes and Terraform skills lead cloud hiring", capability=["Kubernetes", "Terraform"]),
    case("GitHub Copilot now writes tests automatically", capability=["GitHub Copilot", "GitHub"]),
    case("Rust overtakes C++ in new systems projects", capability=["Rust", "C++"]),
    case("TypeScript 6 lands with faster builds", capability=["TypeScript"]),
    case("React.js and Next.js dominate front-end surveys", capability=["React.js", "Next.js"]),
    case("Google Cloud outage disrupts services worldwide", company=["Google"], capability=["Google Cloud Platform"], topic=["Software Outages"]),
    case("AWS announces new region in Hyderabad", capability=["AWS"]),
    case("TCS layoffs spark debate on hiring trends", company=["Tata Consultancy Services"], topic=["Layoffs", "Hiring Trends"]),
    case("Infosys campus hiring resumes for freshers", company=["Infosys"], capability=["Campus Hiring"], topic=["Campus Hiring Season"]),
    case("Return to office mandates return as hybrid work rethink begins", topic=["Remote and Hybrid Work"]),
    case("Salary hikes cool as attrition rate eases", topic=["Compensation Trends", "Attrition"]),
    case("Ransomware gang hits hospital network", topic=["Cybersecurity Threats"]),
    case("CrowdStrike outage grounds flights", capability=["CrowdStrike"], topic=["Software Outages"]),
    case("Critical zero-day found in Windows Server", capability=["Windows Server"], topic=["Vulnerabilities and Patches"]),
    case("Data breach exposes customer records at retailer", topic=["Data Breaches"]),
    case("Zero Trust adoption climbs across banks", capability=["Zero Trust"]),
    case("OpenAI releases a larger large language model", company=["OpenAI"], capability=["Large Language Models"]),
    case("Nvidia GPUs demand lifts data centres", company=["Nvidia"], topic=["AI Chips and Compute"]),
    case("Snowflake and Databricks compete for data engineers", company=["Snowflake", "Databricks"], capability=["Snowflake", "Databricks"]),
    case("PyTorch 3.0 adds better compilation", capability=["PyTorch"]),
    case("Retrieval-Augmented Generation moves into production", capability=["Retrieval-Augmented Generation"]),
    case("Supply chain disruption hits carmakers as Red Sea attacks continue", topic=["Supply Chain Disruption", "Ports and Trade"]),
    case("Maersk raises freight rates on Asia-Europe routes", company=["Maersk"], topic=["Freight and Shipping Rates"]),
    case("Tariffs and export controls reshape electronics trade", topic=["Tariffs and Trade Policy"]),
    case("Six Sigma and Lean Manufacturing help plants cut defects", capability=["Six Sigma", "Lean Manufacturing"]),
    case("SAP S/4HANA migrations slow as budgets tighten", capability=["SAP"], company=["SAP SE"]),
    case("Warehouse automation spending doubles", topic=["Warehouse Automation"]),
    case("Salesforce reports earnings ahead of estimates", company=["Salesforce"]),
    case("Enterprise sales teams chase ARR growth", capability=["Enterprise Sales"], topic=["Enterprise Software Sales"]),
    case("Figma unveils design system tools", capability=["Figma", "Design Systems"]),
    case("Product Analytics teams standardise on Amplitude and Mixpanel", capability=["Product Analytics", "Amplitude", "Mixpanel"]),
    case("McKinsey says consulting firms are cutting graduate intakes", company=["McKinsey & Company"], topic=["Consulting Industry"]),
    case("PwC, EY and KPMG face audit scrutiny", company=["PwC", "EY", "KPMG"]),
    case("Six-figure salaries for Machine Learning engineers", capability=["Machine Learning"]),
    case("Meta unveils a new AI model for developers", company=["Meta Platforms"]),
    case("Oracle Database 23ai launches with vector search", company=["Oracle"], capability=["Oracle Database", "Vector Databases"]),
]

# --- Must NOT tag -------------------------------------------------------------------------------
NEGATIVE = [
    case("Amazon rainforest fires hit record levels"),
    case("Deforestation in the Amazon accelerates"),
    case("Rust Belt manufacturers brace for change", topic=[]),
    case("How to excel at your next interview"),
    case("Amazon once sold a Rs 185 Surf Excel pack for Rs 82,740", company=["Amazon India"]),
    case("Apple juice prices climb as harvest shrinks"),
    case("Taylor Swift tour boosts local economies"),
    case("Oracle of Omaha Warren Buffett buys more shares"),
    case("Harrison Ford returns in a new film"),
    case("West Java floods displace thousands"),
    case("La Scala opens its new season"),
    case("Visa applications surge at consulates"),
    case("Python found in Mumbai apartment, rescued by snake handlers"),
    case("Tally of votes continues across the state"),
    case("Airflow restrictions at the airport disrupt travel"),
    case("Local council approves new park budget"),
    case("React to the announcement calmly, experts say"),
    case("Angular momentum explained for students"),
    case("Meta description best practices for blogs"),
    case("How to grow your Instagram audience without Reels"),
    case("Meta-analysis finds mixed results for the treatment"),
    case("Nestle chief steps down after decade at the helm"),
    case("Celebrity chef opens a restaurant in Delhi"),
]

ALL_CASES = POSITIVE + NEGATIVE
