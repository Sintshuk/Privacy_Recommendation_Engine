RIGHT_TYPE = {
    "Right of access": {
        "description": (
            "1. Any data subject that requests to know whether or not personal data concerning him or her are being "
            "collected and processed, the organization must provide access to the personal data of the data subject. "
            "The data subject is entitled to receive the following information: (a) the purposes of the processing; "
            "(b) the categories of personal data concerned; (c) the recipients or categories of recipient to whom the "
            "personal data have been or will be disclosed, in particular recipients in third countries or international "
            "organisations; (d) where possible, the envisaged period for which the personal data will be stored, or, "
            "if not possible, the criteria used to determine that period; (e) the existence of the right to request "
            "from the controller rectification or erasure of personal data or restriction of processing of personal "
            "data concerning the data subject or to object to such processing; (f) the right to lodge a complaint with "
            "a supervisory authority; (g) where the personal data are not collected from the data subject, any "
            "available information as to their source; (h) the existence of automated decision-making, including "
            "profiling, meaningful information about the logic involved, as well as the significance and the "
            "envisaged consequences of such processing for the data subject. 2. Where personal data are transferred "
            "to a third country or to an international organisation, the data subject shall have the right to be "
            "informed of the appropriate safeguards relating to the transfer. 3. The controller (i.e., the first "
            "party) shall provide a copy of the personal data undergoing processing."
        ),
        "examples": [
            "you have the right to know what personal data we hold about you",
            "you may request a copy of your personal data",
            "obtain a copy of your information",
            "right to access",
            "right to know",
            "confirm whether we process your data",
            "request that we disclose the categories and specific pieces of personal information we collected",
        ],
        "note": (
            "This value also includes a stated right to lodge a complaint with a "
            "supervisory, regulatory, statutory, privacy, or data-protection authority, "
            "because clause (f) in this schema treats that entitlement as part of "
            "Right of access. Do not map a complaint to an external authority to the "
            "choice_type value 'Lodge a complaint'."
        ),
    },
    "Right to rectification": {
        "description": (
            "Data subjects have right to rectification of inaccurate personal information as well as right to have "
            "incomplete personal data completed, including by means of providing a supplementary statement, "
            "concerning him/her."
        ),
        "examples": [
            "you may correct or update inaccurate or incomplete information",
            "right to rectification",
            "right to correct",
        ],
    },
    "Right to erasure": {
        "description": (
            "Data subjects have right to have their personal data erased where one of the following grounds applies: "
            "(1) the personal data are no longer necessary in relation to the purposes for which they were collected "
            "or otherwise processed; (2) the lawful basis for the processing is the data subject's consent, the data "
            "subject withdraws that consent, and where there is no other legal ground for the processing; (3) the "
            "data subject exercises the right to object, and there are no overriding legitimate grounds for the "
            "processing; (4) the personal data have been unlawfully processed; (5) the personal data have to be "
            "erased for compliance with a legal obligation in Union or Member State law to which the controller is "
            "subject; (6) the personal data have been collected in relation to the offer of information society "
            "services."
        ),
        "examples": [
            "you may request deletion of your personal data",
            "right to erasure",
            "right to be forgotten",
            "ask us to delete the information we hold about you",
        ],
        "note": "Withdrawing consent alone is NOT this value",
    },
    "Right to restriction of processing": {
        "description": (
            "Data subjects have the right to restrict the processing of their personal data if: (1) the accuracy of "
            "the personal data is contested by the data subject, for a period enabling the controller to verify the "
            "accuracy of the personal data; (2) the processing is unlawful and the data subject opposes the erasure "
            "of the personal data and requests the restriction of their use instead; (3) the controller no longer "
            "needs the personal data for the purposes of the processing, but the data is still required to establish, "
            "exercise or defend legal rights; (4) the data subject has objected to processing pending the "
            "verification whether the legitimate grounds of the controller override those of the data subject."
        ),
        "examples": [
            "you may request that we restrict the processing of your data",
            "ask us to limit how we use your information",
        ],
    },
    "Obligation to notify recipients": {
        "description": (
            "The controller (i.e., the first party) shall communicate any rectification or erasure of personal data "
            "or restriction of processing carried out to each recipient to whom the personal data have been "
            "disclosed. The controller shall inform the data subject about those recipients if the data subject "
            "requests it."
        ),
        "examples": [
            "we will notify recipients of the correction or deletion",
            "we will inform parties to whom the data was disclosed",
        ],
    },
    "Right to data portability": {
        "description": (
            "The data subjects have the right to receive their own personal data, which they have provided to a "
            "controller, in a structured, commonly used and machine-readable format. They also have the right to "
            "transmit the data to another controller without hindrance from the controller, where: (1) 'lawful "
            "processing criteria' is either consent or Performance of contract; and (2) the processing is carried "
            "out by automated means."
        ),
        "examples": [
            "receive your data in a structured, commonly used and machine-readable format",
            "request data portability",
            "transmit your data to another provider",
        ],
    },
    "Right to object": {
        "description": (
            "(1). The data subject shall have the right to object, whenever a controller justifies the data "
            "processing on the basis of its legitimate interests. As a consequence, the controller is no longer "
            "allowed to process the data subject's personal data unless it can demonstrate compelling, legitimate "
            "grounds for the processing. (2). Where personal data are processed for direct marketing purposes, the "
            "data subject shall have the right to object at any time to processing of personal data concerning him "
            "or her for such marketing, which includes profiling to the extent that it is related to such direct "
            "marketing. (3). Where the data subject objects to processing for direct marketing purposes, the "
            "personal data shall no longer be processed for such purposes. (4) In cases where personal data is "
            "processed for scientific and historical research purposes or statistical purposes, the right to object "
            "exists only as far as the processing is not considered necessary for the performance of a task carried "
            "out for reasons of public interest."
        ),
        "examples": [
            "you may object to the processing of your personal data",
            "opt out of processing based on legitimate interests",
            "object to direct marketing",
        ],
        "note": "Only use this value if the text uses formal rights language ('right to object', 'you have the right to').",
    },
    "Right to not be subject to automated decision-making (to profiling)": {
        "description": (
            "(1) The data subject shall have the right not to be subject to a decision based solely on automated "
            "processing, including profiling, which produces legal effects concerning him or her or similarly "
            "significantly affects him or her. (2) Paragraph (1) shall not apply if the decision: (a) is necessary "
            "for entering into, or performance of, a contract between the data subject and a data controller; (b) is "
            "based on the data subject's explicit consent."
        ),
        "examples": [
            "you have the right not to be subject to automated decision-making, including profiling",
            "decisions producing legal or similarly significant effects",
            "request human review of an automated decision",
        ],
    },
    "Other": {
        "description": (
            "A right is described that is not in the value list (e.g., right to appeal a denied request, right to "
            "non-discrimination for exercising rights, posthumous data rights). Record the verbatim right in <...> "
            "format."
        ),
        "examples": [
            "we will not discriminate against you for exercising your rights",
            "requests concerning a deceased user's data",
        ],
    },
}

CHOICE_TYPE = {
    "View and update personal data": {
        "description": (
            "A self-service control lets the individual view, edit, or update personal data or account information. "
            "This also include the possibility for the data subject to download the copy of such data."
        ),
        "examples": [
            "you can view and update your information in your account settings",
            "edit your details in the app or web portal",
            "edit your profile",
            "manage your account information",
        ],
    },
    "Lodge a complaint": { 
        "description": "The individual can raise a complaint or concern directly with the company itself about how their personal data is handled, rather than with an external regulator.", 
        "examples": [ "you may lodge a complaint by emailing us at",
            "you can complain to us", 
            "if you are unhappy with how we have handled your personal data, please contact us", 
        ], 
        "note": (
            "Use only when the complaint or concern is directed to the company "
            "or organisation itself. A complaint to a supervisory, statutory, "
            "regulatory, or data-protection authority is not this choice value."
        ), 
    },
    "Manage notifications and communications": {
        "description": "The individual can choose which service, marketing, push, email, text, or other communications to receive.",
        "examples": [
            "manage your communication preferences",
            "turn off push notifications",
            "choose which emails or texts you receive",
            "unsubscribe link in our emails", 
        ],
    },
    "Delete personal data or account": {
        "description": "A self-service control lets the individual delete data, content, a device history, or an account.",
        "examples": [
            "delete your account in the app",
            "remove your data from the dashboard",
            "delete a recording or activity",
        ],
    },
    "Change or withdraw consent": {
        "description": "The individual can give, modify, or withdraw previously given consent or permission.",
        "examples": [
            "withdraw your consent at any time",
            "change your consent settings",
            "revoke permission",
            "you have the withdraw your consent",
        ],
        "note": "This is the correct value whenever the text says 'withdraw consent' - never tag this as right_type 'Right to erasure'.",
    },
    "Opt out of marketing": {
        "description": "User can opt out of direct marketing communications.",
        "examples": [
            "reply STOP to text messages",
            "opt out of marketing communications",
            "disable promotional push notifications",
        ],
    },
    "Opt out of sale, sharing, or targeted advertising": {
        "description": (
            "The individual can opt out of sale, sharing for cross-context behavioural advertising, or processing "
            "for targeted advertising."
        ),
        "examples": [
            "Do Not Sell or Share My Personal Information",
            "opt out of targeted advertising",
            "opt out of cross-context behavioral advertising",
        ],
    },
    "Device and app permission controls": {
        "description": (
            "Data subject can enable/disable device- or OS-level data capture: sensor permissions, location, "
            "microphone/camera, physical controls on the device."
        ),
        "examples": [
            "disable location access in your device settings",
            "turn off the microphone/camera",
            "revoke app permissions",
            "physical mute switch on the device",
        ],
    },
    "Data sharing and integration controls": {
        "description": (
            "The individual can start, limit, stop, revoke, or manage sharing with other users, connected apps, "
            "integrations, or third parties."
        ),
        "examples": [
            "disconnect the integration",
            "choose what data is shared",
            "revoke a third-party app connection",
            "disable vehicle data sharing",
        ],
    },
    "Other": {
        "description": "A practical privacy control is explicitly described but does not fit a listed value. Record it verbatim in <...> format.",
        "examples": ["<other explicit privacy control>"],
    },
}

REQUEST_CHANNEL = {
    "Online self-service portal": {
        "description": "A dedicated privacy-management centre, dashboard, or authenticated request portal is provided.",
        "examples": [
            "privacy dashboard",
            "account portal",
            "submit a request through our privacy portal",
            "rights request web form",
        ],
    },
    "Device control": {
        "description": "A physical switch, button, shutter, indicator, or device interface performs the privacy action.",
        "examples": [
            "close a camera shutter",
            "press a mute button",
            "device privacy mode",
            "use the in-vehicle data-sharing control",
        ],
    },
    "Request by email": {
        "description": "An email address is explicitly provided for exercising the right or choice.",
        "examples": [
            "a dedicated contact address such as privacy@..., dpo@..., dataprotection@...",
            "email us at ... to exercise your rights",
            "send your request to our data-protection email address",
        ],
    },
    "Request by post": {
        "description": "A postal address is explicitly provided for exercising the right or choice.",
        "examples": ["write to us at [postal address]", "mail your privacy request to"],
    },
    "In-app or device settings": {
        "description": "The right or choice can be exercised through settings in an app, account, browser, or the IoT device (for example via touchscreen).",
        "examples": [
            "in the app settings",
            "from the settings menu on the device or in the companion app",
            "manage this in Settings > Privacy",
            "Controls > Software > Data Sharing",
        ],
    },
    "Web page or online form": {
        "description": "A web page, hyperlink, or online form is explicitly provided for the request or setting.",
        "examples": [
            "visit this page to manage your preferences",
            "submit the online request form",
            "follow the link to exercise your right",
        ],
    },
    "Phone / toll-free number": {
        "description": "A telephone number is explicitly provided for exercising the right or choice.",
        "examples": [
            "call us toll-free at 1-800-...",
            "contact us by phone to submit your request",
        ],
    },
    "Other": {
        "description": "A request channel is explicit but does not fit a listed value. Record it verbatim in <...> format.",
        "examples": ["<chat, in-person, or another explicit channel>"],
    },
    "Not specified": {
        "description": "A right or choice is clearly described, but no method for exercising it is provided in the segment or linked context.",
        "examples": ["you have the right to object", "with no stated contact method or setting"],
        "note": "Use only after the right or choice itself has been established; never use to create a rights annotation on a heading or overview.",
    },
}

PARENTAL_CONSENT_ATTRIBUTE = "Parental or guardian consent requirement"
PARENTAL_CONSENT_VALUE = {
    "Required": {
        "description": "The segment explicitly states that consent, permission, or authorisation from a parent or guardian is required for a child's processing or use of the service.",
        "examples": [
            "with verified parental consent",
            "consent from a parent or guardian",
            "parental authorisation is required",
        ],
        "note": "Do not treat a general statement that the service is not directed to children as parental consent unless consent is explicitly mentioned.",
    },
}