"""News topics for fields whose roles come from the O*NET import rather than hand-written lists."""

TOPICS_BY_DOMAIN: dict[str, str] = {
    "healthcare": """
Healthcare Delivery | hospital chains; patient care; healthcare providers; hospital capacity
Drug Approvals | FDA approval; drug approval; USFDA; clinical trial results
Health Insurance and Costs | health insurance; healthcare costs; Medicare; Ayushman Bharat
Nursing and Clinical Workforce | nursing shortage; nurses; clinical staff; doctors' strike
Digital Health | telemedicine; digital health; health tech; electronic health records
""",
    "engineering": """
Infrastructure Projects | infrastructure project; highway project; metro rail; bridge construction
Energy Transition Projects | solar plant; wind farm; green hydrogen; battery storage
Aerospace and Defence | aircraft order; defence contract; satellite launch; fighter jets
Engineering Talent | engineering graduates; engineering jobs; engineers shortage
Manufacturing Investment | new plant; manufacturing investment; production-linked incentive; PLI scheme
""",
    "legal": """
Court Rulings | Supreme Court; High Court; court ruling; verdict
Antitrust and Competition | antitrust; competition regulator; monopoly; CCI probe
Corporate Governance and Insolvency | corporate governance; shareholder lawsuit; insolvency; IBC
Intellectual Property | patent; patents; copyright lawsuit; trademark dispute
Compliance Enforcement | regulatory fine; compliance failure; enforcement action; penalty imposed
""",
    "education": """
Higher Education | universities; higher education; college admissions; campus life
EdTech | edtech; online learning; online courses; MOOCs
Education Policy | education policy; National Education Policy; board exams; NEET; JEE
Vocational Training | vocational training; apprenticeships; ITI; skill development scheme
Teaching Profession | teachers; teacher recruitment; school teachers; faculty hiring
""",
    "creative-media": """
Film and Streaming | streaming platform; box office; OTT release; film release
Publishing and News Media | newsroom; news publishers; journalism; news industry
Music and Audio | music industry; podcasts; record label; music streaming
Creative Industry | creative industry; animation studios; VFX; illustrators
Sports Business | IPL; sports broadcasting; team sponsorship; sports leagues
""",
    "trades": """
Construction Activity | construction sector; construction spending; building permits; housing starts
Skilled Trades Shortage | skilled trades; electricians; plumbers; trade workers
Housing and Real Estate | housing market; real estate prices; home sales; property market
Building Materials | building materials; cement prices; steel prices; lumber
Workplace Safety | site accident; workplace safety; safety violations; construction accident
""",
    "public-services": """
Public Policy | government policy; policy reform; Union Cabinet; new legislation
Public Safety | police; fire department; emergency services; disaster response
Social Services | social welfare; NGOs; social work; charity
Defence and Armed Forces | armed forces; military; defence ministry; army
Civil Services | civil services; UPSC; government jobs; public sector recruitment
""",
    "hospitality": """
Travel and Tourism | tourism; travel demand; tourist arrivals; holiday bookings
Restaurants and Food Service | restaurants; food service; quick service restaurants; QSR
Hotels and Lodging | hotel occupancy; hospitality industry; resorts; hotel chains
Events and Entertainment Venues | live events; concerts; theme parks; event industry
Aviation and Airlines | airlines; air traffic; aircraft deliveries; airport traffic
""",
    "science": """
Scientific Research | peer-reviewed study; researchers found; scientific study; new study finds
Space and Astronomy | space mission; ISRO; rocket launch; space telescope
Climate Science | climate change; global warming; climate research; emissions data
Biotech and Genomics | genomics; CRISPR; gene therapy; mRNA
Quantum Research | quantum computing research; quantum chip; qubits; quantum advantage
""",
    "admin": """
Office Space and Workplaces | office leasing; coworking; workspace demand; facilities management
Business Process Outsourcing | BPO; call centre; global capability centres; GCC
Office Administration | executive assistants; office management; administrative jobs; clerical
Small Business Operations | small business owners; SMB owners; family businesses
Data Entry and Back Office | back office; data entry; records management; document processing
""",
    "agriculture": """
Crop and Farm Output | crop yield; farm output; monsoon; kharif
Food Prices and Supply | food prices; food inflation; vegetable prices; edible oil prices
AgriTech | agritech; precision farming; farm technology; farmers app
Environment and Conservation | biodiversity; wildlife conservation; forest cover; air pollution
Farm Policy | minimum support price; MSP; farm laws; fertiliser subsidy
""",
}
