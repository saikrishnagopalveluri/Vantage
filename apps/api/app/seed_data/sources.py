"""Official RSS/Atom feeds only. (name, feed_url, authority 1-5). Every URL here answered with a
valid feed when last probed; a source that later breaks is recorded, not fatal (see ingest)."""

SOURCES: list[tuple[str, str, int]] = [
    # Marketing, retail and customer experience
    ("Marketing Dive", "https://www.marketingdive.com/feeds/news/", 4),
    ("Marketing Week", "https://www.marketingweek.com/feed/", 4),
    ("Adweek", "https://www.adweek.com/feed/", 4),
    ("Google Ads & Commerce Blog", "https://blog.google/products/ads-commerce/rss/", 5),
    ("Social Media Examiner", "https://feeds.feedburner.com/SocialMediaExaminer", 3),
    ("Retail Dive", "https://www.retaildive.com/feeds/news/", 4),
    ("Customer Experience Dive", "https://www.customerexperiencedive.com/feeds/news/", 4),
    # India business and markets
    ("Mint - Companies", "https://www.livemint.com/rss/companies", 4),
    ("Mint - Markets", "https://www.livemint.com/rss/markets", 4),
    ("Mint - Economy", "https://www.livemint.com/rss/economy", 4),
    ("Economic Times - FMCG", "https://economictimes.indiatimes.com/industry/cons-products/fmcg/rssfeeds/13358259.cms", 4),
    ("Economic Times - Markets", "https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms", 4),
    ("Economic Times - Tech", "https://economictimes.indiatimes.com/tech/rssfeeds/13357270.cms", 4),
    ("Economic Times - Jobs", "https://economictimes.indiatimes.com/jobs/rssfeeds/107115.cms", 3),
    ("BusinessLine - Companies", "https://www.thehindubusinessline.com/companies/feeder/default.rss", 4),
    ("BusinessLine - Markets", "https://www.thehindubusinessline.com/markets/feeder/default.rss", 4),
    ("RBI Press Releases", "https://www.rbi.org.in/pressreleases_rss.xml", 5),
    # Finance and banking
    ("CNBC - Finance", "https://www.cnbc.com/id/10000664/device/rss/rss.html", 4),
    ("CFO Dive", "https://www.cfodive.com/feeds/news/", 4),
    ("Banking Dive", "https://www.bankingdive.com/feeds/news/", 4),
    ("PYMNTS", "https://www.pymnts.com/feed/", 3),
    ("Finextra", "https://www.finextra.com/rss/headlines.aspx", 4),
    # Technology, engineering, data and AI
    ("Ars Technica", "https://feeds.arstechnica.com/arstechnica/index", 4),
    ("The Verge", "https://www.theverge.com/rss/index.xml", 3),
    ("TechCrunch", "https://techcrunch.com/feed/", 3),
    ("Wired", "https://www.wired.com/feed/rss", 3),
    ("ZDNet", "https://www.zdnet.com/news/rss.xml", 3),
    ("Computer Weekly", "https://www.computerweekly.com/rss/All-Computer-Weekly-content.xml", 4),
    ("InfoQ", "https://feed.infoq.com/", 4),
    ("GitHub Blog", "https://github.blog/feed/", 5),
    ("AWS News Blog", "https://aws.amazon.com/blogs/aws/feed/", 5),
    ("Google Cloud Blog", "https://cloudblog.withgoogle.com/rss/", 5),
    ("MIT Technology Review", "https://www.technologyreview.com/feed/", 5),
    ("OpenAI News", "https://openai.com/blog/rss.xml", 5),
    ("NVIDIA Blog", "https://blogs.nvidia.com/feed/", 4),
    ("KDnuggets", "https://www.kdnuggets.com/feed", 3),
    # Security
    ("Krebs on Security", "https://krebsonsecurity.com/feed/", 5),
    ("BleepingComputer", "https://www.bleepingcomputer.com/feed/", 4),
    ("The Hacker News", "https://thehackernews.com/feeds/posts/default", 4),
    # Operations and supply chain
    ("Supply Chain Dive", "https://www.supplychaindive.com/feeds/news/", 4),
    ("Manufacturing Dive", "https://www.manufacturingdive.com/feeds/news/", 4),
    ("FreightWaves", "https://www.freightwaves.com/news/feed", 4),
    # HR
    ("HR Dive", "https://www.hrdive.com/feeds/news/", 4),
    ("ETHRWorld", "https://hr.economictimes.indiatimes.com/rss/topstories", 3),
    # Consulting and strategy
    ("McKinsey Insights", "https://www.mckinsey.com/insights/rss", 5),
    # Healthcare
    ("Fierce Healthcare", "https://www.fiercehealthcare.com/rss/xml", 4),
    ("Healthcare Dive", "https://www.healthcaredive.com/feeds/news/", 4),
    ("STAT", "https://www.statnews.com/feed/", 5),
    ("MedCity News", "https://medcitynews.com/feed/", 3),
    ("Fierce Pharma", "https://www.fiercepharma.com/rss/xml", 4),
    # Construction, energy and manufacturing
    ("Construction Dive", "https://www.constructiondive.com/feeds/news/", 4),
    ("Utility Dive", "https://www.utilitydive.com/feeds/news/", 4),
    ("Waste Dive", "https://www.wastedive.com/feeds/news/", 3),
    # Education
    ("Education Dive", "https://www.educationdive.com/feeds/news/", 4),
    ("K-12 Dive", "https://www.k12dive.com/feeds/news/", 4),
    ("Higher Ed Dive", "https://www.highereddive.com/feeds/news/", 4),
    ("EdSurge", "https://www.edsurge.com/articles_rss", 3),
    # Law
    ("Above the Law", "https://abovethelaw.com/feed/", 3),
    # Hospitality and travel
    ("Skift", "https://skift.com/feed/", 4),
    ("Eater", "https://www.eater.com/rss/index.xml", 3),
    ("Restaurant Dive", "https://www.restaurantdive.com/feeds/news/", 4),
    # Media, entertainment and design
    ("Variety", "https://variety.com/feed/", 4),
    ("Deadline", "https://deadline.com/feed/", 4),
    ("The Hollywood Reporter", "https://www.hollywoodreporter.com/feed/", 4),
    ("Design Week", "https://www.designweek.co.uk/feed/", 3),
    ("Creative Bloq", "https://www.creativebloq.com/feeds.xml", 3),
    # Science and agriculture
    ("Nature", "https://www.nature.com/nature.rss", 5),
    ("ScienceDaily", "https://www.sciencedaily.com/rss/top/science.xml", 3),
    ("Phys.org", "https://phys.org/rss-feed/", 3),
    ("AgFunder News", "https://agfundernews.com/feed", 3),
    ("Mongabay", "https://news.mongabay.com/feed/", 3),
    ("Farm Progress", "https://www.farmprogress.com/rss.xml", 3),
    # Digital transformation, platforms and B2B
    ("CIO", "https://www.cio.com/feed/", 4),
    ("MIT Sloan Management Review", "https://sloanreview.mit.edu/feed/", 4),
    ("B2B Marketing", "https://www.b2bmarketing.net/feed", 3),
    ("Modern Retail", "https://www.modernretail.co/feed/", 3),
    # Business schools and management
    ("Poets&Quants", "https://poetsandquants.com/feed/", 3),
    ("Knowledge at Wharton", "https://knowledge.wharton.upenn.edu/feed/", 4),
    ("Ivey Business Journal", "https://iveybusinessjournal.com/feed/", 3),
    ("The Economist - Business", "https://www.economist.com/business/rss.xml", 4),
    ("Financial Times - Companies", "https://www.ft.com/companies?format=rss", 4),
    # Indian business, startups and brands
    ("Business Today", "https://www.businesstoday.in/rss/latest", 3),
    ("Fortune India", "https://www.fortuneindia.com/feed", 3),
    ("Economic Times - Industry", "https://economictimes.indiatimes.com/industry/rssfeeds/13352306.cms", 4),
    ("Economic Times - Startups", "https://economictimes.indiatimes.com/small-biz/startups/rssfeeds/11993050.cms", 4),
    ("Economic Times - Wealth", "https://economictimes.indiatimes.com/wealth/rssfeeds/837555174.cms", 3),
    ("ET CFO", "https://cfo.economictimes.indiatimes.com/rss/topstories", 3),
    ("ET BrandEquity", "https://brandequity.economictimes.indiatimes.com/rss/topstories", 3),
    ("afaqs", "https://www.afaqs.com/rss", 3),
    ("Inc42", "https://inc42.com/feed/", 3),
    ("YourStory", "https://yourstory.com/feed", 3),
]

SAMPLE_SOURCE = ("Vantage Samples (placeholder)", "vantage://samples", 1)
