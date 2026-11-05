from django.conf import settings


PUBLIC_UI_COPY = {
    "en": {
        "skip_link": "Skip to main content",
        "brand_name": "Farm Time Machine",
        "brand_tagline": "Understand yesterday. Prepare for tomorrow.",
        "nav_label": "Main navigation",
        "nav_home": "Home",
        "nav_weather": "Weather",
        "nav_history": "Historical Data",
        "nav_crop_insights": "Crop Insights",
        "nav_how_it_works": "How It Works",
        "nav_about": "About",
        "language": "Language",
        "dashboard": "Dashboard",
        "login": "Log in",
        "signup": "Sign up",
        "footer_summary": "Evidence-aware agricultural planning with transparent data, practical tools, and human expertise.",
        "footer_explore": "Explore",
        "footer_platform": "Platform",
        "footer_support": "Support",
        "footer_learning": "Learning Center",
        "footer_data_sources": "Data sources",
        "footer_help": "Help",
        "footer_contact": "Contact",
        "footer_privacy": "Privacy",
        "footer_terms": "Terms",
        "footer_disclaimer": "A decision-support tool, not a substitute for qualified agricultural advice.",
        "home_eyebrow": "Public agricultural insights",
        "home_title_first": "Understand the Past.",
        "home_title_second": "Plan a Better Harvest.",
        "home_description": "Explore weather, historical rainfall, heat trends, and crop signals for Bangladesh without signing in. Save farms and decisions when you are ready.",
        "home_explore_history": "Explore Farm History",
        "home_get_started": "Get Started",
    },
    "bn": {
        "skip_link": "মূল বিষয়বস্তুতে যান",
        "brand_name": "ফার্ম টাইম মেশিন",
        "brand_tagline": "গতকাল বুঝুন। আগামীর জন্য প্রস্তুত হোন।",
        "nav_label": "প্রধান নেভিগেশন",
        "nav_home": "হোম",
        "nav_weather": "আবহাওয়া",
        "nav_history": "ঐতিহাসিক তথ্য",
        "nav_crop_insights": "ফসলের তথ্য",
        "nav_how_it_works": "কীভাবে কাজ করে",
        "nav_about": "পরিচিতি",
        "language": "ভাষা",
        "dashboard": "ড্যাশবোর্ড",
        "login": "লগ ইন",
        "signup": "নিবন্ধন",
        "footer_summary": "স্বচ্ছ তথ্য, ব্যবহারিক সরঞ্জাম ও মানবিক দক্ষতায় প্রমাণভিত্তিক কৃষি পরিকল্পনা।",
        "footer_explore": "অন্বেষণ",
        "footer_platform": "প্ল্যাটফর্ম",
        "footer_support": "সহায়তা",
        "footer_learning": "শিক্ষাকেন্দ্র",
        "footer_data_sources": "তথ্যের উৎস",
        "footer_help": "সহায়তা",
        "footer_contact": "যোগাযোগ",
        "footer_privacy": "গোপনীয়তা",
        "footer_terms": "শর্তাবলি",
        "footer_disclaimer": "এটি সিদ্ধান্ত-সহায়ক সরঞ্জাম; যোগ্য কৃষি বিশেষজ্ঞের পরামর্শের বিকল্প নয়।",
        "home_eyebrow": "সবার জন্য কৃষি তথ্য",
        "home_title_first": "অতীতকে বুঝুন।",
        "home_title_second": "ভালো ফসলের পরিকল্পনা করুন।",
        "home_description": "সাইন ইন ছাড়াই বাংলাদেশের আবহাওয়া, ঐতিহাসিক বৃষ্টিপাত, তাপমাত্রার প্রবণতা ও ফসলের সংকেত দেখুন। প্রস্তুত হলে খামার ও সিদ্ধান্ত সংরক্ষণ করুন।",
        "home_explore_history": "খামারের ইতিহাস দেখুন",
        "home_get_started": "শুরু করুন",
    },
}


def platform_context(request):
    unread_count = 0
    recent_notifications = []
    if request.user.is_authenticated:
        try:
            notifications = request.user.notifications.order_by("-created_at")
            unread_count = notifications.filter(read_at__isnull=True).count()
            recent_notifications = notifications[:5]
        except (AttributeError, TypeError):
            pass
    language_code = getattr(request, "LANGUAGE_CODE", settings.LANGUAGE_CODE).split("-", 1)[0]
    if language_code not in PUBLIC_UI_COPY:
        language_code = "en"
    return {
        "platform_name": "Farm Time Machine",
        "demo_mode": settings.DEMO_MODE,
        "unread_notification_count": unread_count,
        "recent_notifications": recent_notifications,
        "public_ui": PUBLIC_UI_COPY[language_code],
        "active_language": language_code,
    }
