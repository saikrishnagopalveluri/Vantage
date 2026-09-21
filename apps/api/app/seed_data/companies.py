"""Companies by industry. Each hires for the domains listed in common.INDUSTRY_DOMAINS."""

COMPANIES = """
# FMCG
Hindustan Unilever | fmcg | HUL; Hindustan Unilever Ltd
ITC | fmcg | ITC Limited
Nestle India | fmcg | Nestlé India
Procter & Gamble | fmcg | P&G; Procter and Gamble
Colgate-Palmolive | fmcg | Colgate
Dabur | fmcg
Britannia | fmcg | Britannia Industries
Marico | fmcg
Godrej Consumer Products | fmcg | Godrej Consumer
Coca-Cola | fmcg | Coca Cola
PepsiCo | fmcg
Mondelez | fmcg | Mondelēz
Tata Consumer Products | fmcg | Tata Consumer
Reckitt | fmcg | Reckitt Benckiser
Emami | fmcg
L'Oreal | fmcg | L'Oréal
Amul | fmcg | GCMMF

# E-commerce and consumer internet
Amazon India | ecom | Amazon | avoid:rainforest; avoid:Amazon River; avoid:Amazon basin; avoid:deforestation
Flipkart | ecom
Myntra | ecom
Nykaa | ecom
Meesho | ecom
Zomato | ecom | Eternal Ltd
Swiggy | ecom
BigBasket | ecom
Uber | ecom
Airbnb | ecom

# Software, SaaS and big tech
Google | saas | Alphabet
Microsoft | saas
Meta Platforms | saas | Meta; Facebook | avoid:Meta description; avoid:Meta tag; avoid:Meta title; avoid:Meta-analysis
Apple | saas | | avoid:apple juice; avoid:apple cider; avoid:apple pie; avoid:Big Apple
Adobe | saas
Salesforce | saas
Oracle | saas | | avoid:Oracle of Omaha
SAP SE | saas | SAP AG; SAP
Atlassian | saas
Zoho | saas | Zoho Corporation
Freshworks | saas
Nvidia | semis | NVIDIA
OpenAI | saas
Anthropic | saas
Netflix | media
Spotify | media
Intuit | saas
ServiceNow | saas
Snowflake | saas
Databricks | saas
Palantir | saas
Shopify | saas

# IT services
Tata Consultancy Services | itservices | TCS; Tata Consultancy; TCS India
Infosys | itservices | Infosys Limited; Infosys Consulting; Infosys BPM
Wipro | itservices | Wipro Limited; Wipro Consulting; Wipro Technologies
HCLTech | itservices | HCL Technologies; HCL Tech
Tech Mahindra | itservices
Cognizant | itservices
Accenture | itservices | Accenture Strategy; Accenture India; Accenture Federal Services
Capgemini | itservices | Capgemini Invent; Capgemini India; Capgemini Engineering
LTIMindtree | itservices
IBM | itservices | IBM Consulting; IBM India; International Business Machines

# Banking
HDFC Bank | banking
ICICI Bank | banking
State Bank of India | banking | SBI
Axis Bank | banking
Kotak Mahindra Bank | banking | Kotak Mahindra
JPMorgan Chase | banking | JPMorgan; JP Morgan
Citigroup | banking | Citibank
HSBC | banking
Standard Chartered | banking
Deutsche Bank | banking
Barclays | banking
Bank of America | banking | BofA

# Capital markets and asset management
Goldman Sachs | capmkts
Morgan Stanley | capmkts
BlackRock | assetmgmt
Blackstone | assetmgmt
KKR | assetmgmt
Nomura | capmkts
Zerodha | fintech
Groww | fintech

# Insurance
Life Insurance Corporation | insurance | LIC of India
HDFC Life | insurance
ICICI Prudential | insurance | ICICI Pru
Allianz | insurance
Bajaj Finserv | insurance | Bajaj Finance

# Fintech
Paytm | fintech
PhonePe | fintech
Razorpay | fintech
CRED | fintech
Stripe | fintech
PayPal | fintech
Visa Inc | fintech
Mastercard | fintech

# Consulting
McKinsey & Company | consulting | McKinsey; McKinsey India; McKinsey Global Institute; McKinsey Digital
Boston Consulting Group | consulting | BCG; BCG India; BCG Henderson Institute
Bain & Company | consulting | Bain; Bain India; Bain and Company
Deloitte | consulting | Deloitte Touche Tohmatsu; Deloitte India; Deloitte Consulting; Deloitte US; Deloitte Insights
PwC | consulting | PricewaterhouseCoopers; PwC India; PwC US; PwC Consulting; Price Waterhouse
EY | consulting | Ernst & Young; EY India; EY Global; Ernst and Young
KPMG | consulting | KPMG India; KPMG Advisory; KPMG US; KPMG Global

# Manufacturing and automotive
Tata Motors | auto
Mahindra & Mahindra | auto | Mahindra
Maruti Suzuki | auto
Toyota | auto
Tesla | auto
Ford | auto | Ford Motor | avoid:Harrison Ford; avoid:Gerald Ford; avoid:Betty Ford; avoid:Ford Foundation
Hero MotoCorp | auto
Bajaj Auto | auto
Ashok Leyland | auto
Bosch | mfg
Siemens | mfg
ABB | mfg
Larsen & Toubro | mfg | L&T
Tata Steel | mfg
JSW Steel | mfg
Havells | mfg

# Logistics
Delhivery | logistics
Blue Dart | logistics
DHL | logistics
FedEx | logistics
Maersk | logistics
Mahindra Logistics | logistics

# Pharma and healthcare
Sun Pharma | pharma | Sun Pharmaceutical
Dr. Reddy's | pharma | Dr Reddys
Cipla | pharma
Pfizer | pharma
Apollo Hospitals | healthcare
Johnson & Johnson | pharma | J&J

# Retail
Reliance Retail | retail
DMart | retail | Avenue Supermarts
Walmart | retail
IKEA | retail
Decathlon | retail
Titan Company | retail | Titan Co

# Telecom
Reliance Jio | telecom | Jio Platforms
Bharti Airtel | telecom | Airtel
Vodafone Idea | telecom
Ericsson | telecom
Nokia | telecom

# Energy
Reliance Industries | energy | RIL
ONGC | energy | Oil and Natural Gas Corporation
Adani Group | energy | Adani
Tata Power | energy
NTPC | energy
Indian Oil | energy | IndianOil

# Semiconductors
Intel | semis
AMD | semis
TSMC | semis | Taiwan Semiconductor
Qualcomm | semis

# Media and advertising
WPP | media
Ogilvy | media
Publicis | media | Publicis Groupe
Omnicom | media
Dentsu | media
GroupM | media
Walt Disney | media | Disney

# Healthcare services
Fortis Healthcare | healthcare | Fortis
Max Healthcare | healthcare
Narayana Health | healthcare
HCA Healthcare | healthcare
UnitedHealth Group | healthcare | UnitedHealth

# Real estate
DLF | realestate
Godrej Properties | realestate
Prestige Estates | realestate | Prestige Group
CBRE | realestate
JLL | realestate | Jones Lang LaSalle

# Hospitality and travel
Marriott | hospitality | Marriott International
Hilton | hospitality
Indian Hotels Company | hospitality | Taj Hotels; IHCL
OYO | hospitality | Oyo Rooms
MakeMyTrip | hospitality
Booking Holdings | hospitality | Booking.com
Expedia | hospitality | Expedia Group

# Education
Byju's | education | BYJU'S
upGrad | education
Coursera | education
Pearson | education
Unacademy | education

# Agriculture
Deere & Company | agriculture | John Deere
UPL | agriculture
Nutrien | agriculture
Godrej Agrovet | agriculture

# Chemicals and materials
Asian Paints | materials
UltraTech Cement | materials
BASF | materials
Dow Inc | materials | Dow Chemical
Pidilite | materials | Pidilite Industries
Infra.Market | materials

# Construction
Tata Projects | construction
Bechtel | construction
Fluor | construction | Fluor Corporation

# Utilities
NextEra Energy | utilities
Duke Energy | utilities
Power Grid Corporation of India | utilities | Power Grid

# Mining and metals
BHP | mining | BHP Group
Rio Tinto | mining
Vedanta | mining | Vedanta Resources
Coal India | mining
Hindalco | mining | Hindalco Industries

# Aerospace and defense
Boeing | aerospace
Airbus | aerospace
Lockheed Martin | aerospace
Hindustan Aeronautics | aerospace | HAL

# Transportation and airlines
InterGlobe Aviation | transport | IndiGo
Air India | transport
Delta Air Lines | transport

# Holdings
Berkshire Hathaway | holding
SoftBank Group | holding | SoftBank

# Marketplaces and platforms
Etsy | ecom
eBay | ecom
Upwork | ecom
Fiverr | ecom
Grab | ecom | Grab Holdings
Lyft | ecom
DoorDash | ecom
Instacart | ecom | Maplebear
Urban Company | ecom | UrbanClap
Rapido | ecom
Alibaba | ecom | Alibaba Group

# B2B commerce
IndiaMART | ecom | IndiaMart InterMesh
Udaan | ecom
Moglix | ecom
Jumbotail | ecom
Zetwerk | mfg
OfBusiness | fintech | Oxyzo
Grainger | mfg | W.W. Grainger

# Automation and digital transformation vendors
UiPath | saas
Celonis | saas
Appian | saas
Pegasystems | saas | Pega
Automation Anywhere | saas
"""

# Named in the Managing Digital Transformation and Managing Platform Businesses course handouts.
COMPANIES += """
Farfetch | ecom
Rent the Runway | ecom
Enel | utilities | Enel S.p.A.
Bayer | pharma | Bayer Crop Science | avoid:Bayer Leverkusen; avoid:Leverkusen
American Well | healthcare | Amwell
Wattpad | media
GoFundMe | fintech
Foursquare | saas
Sidewalk Labs | saas
ASICS | fmcg | Asics
On Holding | fmcg | On Running
Odisha Television | media | OTV
"""
