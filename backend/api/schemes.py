from typing import List, Optional
from fastapi import APIRouter, Query

router = APIRouter()

AGRICULTURAL_SCHEMES = [
    {
        "id": 1,
        "name": "PM-KISAN (Pradhan Mantri Kisan Samman Nidhi)",
        "name_ta": "பிஎம்-கிசான் திட்டம்",
        "category": "Direct Income Support",
        "who_can_apply": "All landholding farmer families across India",
        "who_can_apply_ta": "நிலம் வைத்துள்ள அனைத்து விவசாய குடும்பங்கள்",
        "benefits": "₹6,000 per year directly transferred to bank account in 3 equal four-monthly installments of ₹2,000 each.",
        "benefits_ta": "ஆண்டுக்கு ₹6,000, 3 தவணைகளில் (தவணைக்கு ₹2,000) நேரடியாக வங்கி கணக்கில் செலுத்தப்படும்.",
        "eligibility": "Operational agricultural landholders with active Aadhaar eKYC and land ownership records.",
        "eligibility_ta": "ஆதார் eKYC மற்றும் பட்டா சிட்டா ஆவணம் உள்ள விவசாயிகள்.",
        "source": "https://pmkisan.gov.in/"
    },
    {
        "id": 2,
        "name": "PMFBY (Pradhan Mantri Fasal Bima Yojana)",
        "name_ta": "பிரதம மந்திரி பயிர் காப்பீட்டுத் திட்டம்",
        "category": "Crop Insurance",
        "who_can_apply": "All farmers including sharecroppers and tenant farmers growing notified crops in notified areas.",
        "who_can_apply_ta": "அறிவிக்கப்பட்ட பகுதியில் பயிர் செய்யும் அனைத்து விவசாயிகள் மற்றும் குத்தகை விவசாயிகள்.",
        "benefits": "Comprehensive risk coverage against non-preventable natural risks (drought, flood, pests, unseasonal cyclone). Nominal farmer premium: 2% for Kharif, 1.5% for Rabi, 5% for commercial/horticulture.",
        "benefits_ta": "வறட்சி, வெள்ளம், பூச்சித் தாக்குதல் இழப்பிற்கு முழு காப்பீடு. மிகக் குறைந்த பிரீமியம் (1.5% முதல் 2%).",
        "eligibility": "Cultivators of notified crops with sowing certificate and village land passbook.",
        "eligibility_ta": "பயிர் சாகுபடி சான்றிதழ் மற்றும் நில ஆவணங்கள் உள்ள விவசாயிகள்.",
        "source": "https://pmfby.gov.in/"
    },
    {
        "id": 3,
        "name": "PMKSY — Per Drop More Crop (Micro Irrigation Scheme)",
        "name_ta": "சொட்டு நீர் பாசன மானியத் திட்டம் (PMKSY)",
        "category": "Irrigation & Water Conservation",
        "who_can_apply": "Small, marginal, and other farmers possessing assured water sources.",
        "who_can_apply_ta": "பாசன நீர் ஆதாரம் உள்ள சிறு மற்றும் குறு விவசாயிகள்.",
        "benefits": "Up to 100% subsidy for small/marginal farmers in Tamil Nadu (55% Central + 45% State top-up) and 75% for other category farmers for installing Drip & Sprinkler irrigation.",
        "benefits_ta": "சிறு, குறு விவசாயிகளுக்கு 100% மானியம், இதர விவசாயிகளுக்கு 75% மானியத்தில் சொட்டுநீர் பாசனக் கருவிகள்.",
        "eligibility": "Farmers with valid borewell/well/canal source and land records.",
        "eligibility_ta": "கிணறு அல்லது ஆழ்துளை கிணறு பாசன வசதி கொண்ட நில உரிமையாளர்கள்.",
        "source": "https://pmksy.gov.in/"
    },
    {
        "id": 4,
        "name": "Kisan Credit Card (KCC) Scheme",
        "name_ta": "கிசான் கடன் அட்டை திட்டம்",
        "category": "Subsidized Institutional Credit",
        "who_can_apply": "Individual/joint farmers, tenant farmers, self-help groups, animal husbandry and fisheries farmers.",
        "who_can_apply_ta": "தனிநபர் விவசாயிகள், குத்தகை விவசாயிகள் மற்றும் கால்நடை வளர்ப்போர்.",
        "benefits": "Short-term crop production loan up to ₹3,00,000 at concessional interest rate of 7%, reduced to effective 4% per annum upon prompt repayment (3% prompt repayment incentive).",
        "benefits_ta": "₹3 லட்சம் வரை பயிர்க் கடன். உரிய காலத்தில் திருப்பிச் செலுத்தினால் வெறும் 4% குறைந்த வட்டி.",
        "eligibility": "All active farmers with identity, land cultivation or lease documentation.",
        "eligibility_ta": "விவசாயம் செய்யும் விவசாயிகள் மற்றும் குத்தகைதாரர்கள்.",
        "source": "https://myscheme.gov.in/schemes/kcc"
    },
    {
        "id": 5,
        "name": "Tamil Nadu Kalaignarin All Village Integrated Agriculture Development Programme (KAVIADP)",
        "name_ta": "கலைஞரின் அனைத்து கிராம ஒருங்கிணைந்த வேளாண் வளர்ச்சித் திட்டம்",
        "category": "State Integrated Development",
        "who_can_apply": "Farmers in selected Tamil Nadu village panchayats.",
        "who_can_apply_ta": "தேர்ந்தெடுக்கப்பட்ட தமிழக கிராம ஊராட்சிகளில் உள்ள அனைத்து விவசாயிகள்.",
        "benefits": "Free soil health cards, distribution of high-yield certified seeds, coconut saplings, vegetable seed kits, community farm ponds, and conversion of fallow lands into cultivable land.",
        "benefits_ta": "இலவச மண் பரிசோதனை அட்டை, தரமான விதைகள், தென்னங்கன்றுகள், காய்கறி தளைகள் மற்றும் பண்ணைக் குட்டை மானியம்.",
        "eligibility": "Resident agricultural landholders in scheme panchayats with Uzhavan App registration.",
        "eligibility_ta": "உழவன் செயலியில் பதிவு செய்துள்ள கிராம விவசாயிகள்.",
        "source": "https://www.tn.gov.in/department/1"
    }
]

@router.get("/")
def get_schemes(lang: Optional[str] = Query("en"), search: Optional[str] = Query(None)):
    """Returns curated Indian and Tamil Nadu government agricultural schemes and subsidies."""
    results = AGRICULTURAL_SCHEMES
    if search:
        s = search.lower().strip()
        results = [
            scheme for scheme in results
            if s in scheme["name"].lower()
            or s in scheme.get("name_ta", "").lower()
            or s in scheme["category"].lower()
            or s in scheme["benefits"].lower()
        ]
    return results
