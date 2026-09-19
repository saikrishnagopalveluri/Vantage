"""Synthetic articles so the app isn't empty offline. Each title starts with "[Sample]" so nobody
mistakes them for news. (days_ago, title, summary)."""

SAMPLE_ARTICLES: list[tuple[float, str, str]] = [
    (0.3, "[Sample] Hindustan Unilever brand teams lean on Power BI for Campaign ROI Analysis", "Placeholder article showing how a target-company item is explained."),
    (0.6, "[Sample] Interest Rates: RBI holds repo rate as bank lending growth slows", "Placeholder finance story about monetary policy and the banking sector."),
    (0.9, "[Sample] Why data engineers are adopting dbt and Snowflake for analytics pipelines", "Placeholder data-engineering story."),
    (1.1, "[Sample] Supply chain disruption pushes manufacturers toward nearshoring", "Placeholder operations story about supply chains and reshoring."),
    (1.4, "[Sample] Kubernetes and Terraform skills lead cloud hiring demand", "Placeholder story for DevOps and cloud roles."),
    (1.7, "[Sample] Ransomware attack forces hospital group to use Incident Response playbooks", "Placeholder security story."),
    (2.0, "[Sample] Generative AI copilots reshape how Product Managers write specs", "Placeholder product-management story."),
    (2.3, "[Sample] Layoffs slow as campus hiring rebounds at IT services firms", "Placeholder HR story about hiring trends."),
    (2.6, "[Sample] Goldman Sachs analysts turn to Python for Financial Modeling", "Placeholder investment-banking story."),
    (2.9, "[Sample] Enterprise sales teams double down on MEDDIC and Salesforce CRM hygiene", "Placeholder sales story."),
    (3.2, "[Sample] Nestle India tests A/B Testing for pack-price promotions", "Placeholder FMCG experimentation story."),
    (3.5, "[Sample] Design systems and Figma variables cut UI handoff time", "Placeholder design story."),
    (3.8, "[Sample] ITC expands its food portfolio; Brand Strategy in focus", "Placeholder story about ITC brand strategy."),
    (4.1, "[Sample] Six Sigma and Lean Manufacturing help plants cut defects", "Placeholder story about quality and operations."),
    (4.4, "[Sample] Consulting firms hire for Digital Transformation and ESG Reporting work", "Placeholder consulting story."),
    (4.8, "[Sample] Google Analytics 4 reporting changes brand managers should know", "Placeholder marketing analytics story."),
    (5.2, "[Sample] Procter & Gamble doubles down on Retail Media and Excel-free analytics", "Placeholder P&G analytics story."),
    (5.6, "[Sample] Large Language Models move from demos to Retrieval-Augmented Generation in production", "Placeholder generative-AI engineering story."),
    (6.0, "[Sample] Cybersecurity teams adopt Zero Trust and Identity and Access Management upgrades", "Placeholder security architecture story."),
    (6.5, "[Sample] Venture capital funding rebounds; Series A rounds lead the recovery", "Placeholder VC story."),
    (7.0, "[Sample] Warehouse automation and Last-Mile Delivery reshape logistics roles", "Placeholder logistics story."),
    (7.5, "[Sample] Total Rewards and Compensation Benchmarking gain weight in HR strategy", "Placeholder HR compensation story."),
    (8.2, "[Sample] Product Analytics teams standardise on Amplitude and Mixpanel", "Placeholder product-analytics story."),
    (9.0, "[Sample] Influencer Marketing budgets: what Meta Platforms data suggests", "Placeholder influencer-marketing story."),
]
