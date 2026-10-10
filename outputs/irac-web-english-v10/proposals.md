# V10 English intermediate proposals

Four unmodified model proposals; not validated facts.

## 1114159 P

[Raw](runs/1114159/P/raw-response.txt) · [Parsed](runs/1114159/P/parsed.json) · [Submitted task](runs/1114159/P/submitted-task.txt) · [Conversation](https://chatgpt.com/c/6ac86b01-c488-83e8-8b9c-3cd1dc51a2ed?temporary-chat=true)

```json
{
  "records": [
    {
      "text": "The pre-target case account states that the original landlord let the premises to the appellant on 1.10.1961 and that his daughter, the respondent, purchased the property from him on 27th June, 1964, thereby becoming the landlord.",
      "statement_status": "UNKNOWN",
      "refs": ["IK-1114159:L238:restored-v2"]
    },
    {
      "text": "The pre-target account identifies a Rent Note and the appellant's letters dated 7.10.1961 and 18.8.1962, addressed to the original landlord, as documents relied upon by the statutory authorities. Their contents are not reproduced.",
      "statement_status": "RECORDED_DOCUMENT",
      "refs": ["IK-1114159:L239:restored-v2"]
    },
    {
      "text": "Both statutory authorities found that the premises were let for residential purposes but were also used incidentally for commercial purposes. They treated that use as excluding section 14(1)(e) read with its Explanation.",
      "statement_status": "PRIOR_COURT_FINDING",
      "refs": ["IK-1114159:L239:restored-v2"]
    },
    {
      "text": "The High Court found no evidence supporting the statutory authorities' conclusion that the premises had been used for commercial purposes.",
      "statement_status": "PRIOR_COURT_FINDING",
      "refs": ["IK-1114159:L240:span3"]
    },
    {
      "text": "The prior judicial record states that no documentary evidence had been produced to establish that the premises were used for boarding and lodging foreign students.",
      "statement_status": "PRIOR_COURT_FINDING",
      "refs": ["IK-1114159:L241:span4"]
    },
    {
      "text": "The tenant denied parting with exclusive possession of any part of the premises and maintained that the foreign students lodging there were her paying guests rather than tenants.",
      "statement_status": "DENIAL",
      "refs": ["IK-1114159:L244:restored-v2"]
    },
    {
      "text": "The landlord raised a plea of sub-tenancy concerning the foreign students lodging at the premises.",
      "statement_status": "PARTY_CLAIM",
      "refs": ["IK-1114159:L244:restored-v2"]
    },
    {
      "text": "The prior proceedings rejected the landlord's sub-tenancy plea on the ground that the lodgers were paying guests rather than sub-tenants.",
      "statement_status": "PRIOR_COURT_FINDING",
      "refs": ["IK-1114159:L244:restored-v2"]
    }
  ],
  "arrangements": [
    {
      "description": "The appellant's tenancy of premises originally let by the respondent's father on 1.10.1961. The respondent purchased the same property on 27th June, 1964 and became landlord. The subsequent disputed commercial use and foreign-student paying-guest or sub-tenancy accounts concern these premises within the continuing landlord-tenant relationship.",
      "refs": [
        "IK-1114159:L238:restored-v2",
        "IK-1114159:L239:restored-v2",
        "IK-1114159:L240:span3",
        "IK-1114159:L244:restored-v2"
      ]
    }
  ],
  "conditions": [
    {
      "arrangement": 1,
      "condition": "DRC_BONA_FIDE-C01",
      "assessment": "SUPPORTED",
      "evidence": [
        {
          "record": 3,
          "role": "SUPPORT",
          "connection": "The statutory authorities expressly found that the premises were let for residential purposes."
        },
        {
          "record": 2,
          "role": "CONTEXT",
          "connection": "Identifies documents considered by the authorities without supplying their actual terms."
        },
        {
          "record": 4,
          "role": "CONTEXT",
          "connection": "The High Court rejected the evidentiary basis for incidental commercial use, a distinct question from the original letting purpose."
        },
        {
          "record": 6,
          "role": "CONTEXT",
          "connection": "The tenant's account concerns lodgers and possession, not the original letting purpose."
        },
        {
          "record": 8,
          "role": "CONTEXT",
          "connection": "The rejected sub-tenancy plea does not independently determine the original letting purpose."
        }
      ],
      "law_refs": ["IK-18143401:L41:historical-e"],
      "explanation": "The express prior finding of residential letting supports the proposition. The statutory authorities additionally found incidental commercial use, but the High Court found no evidence supporting that conclusion. These conflicting stage-specific findings concern subsequent use and must not be conflated with the original letting purpose. The target court's acceptance remains undetermined.",
      "gaps": [
        "The Rent Note and letters are identified but their contents are not supplied.",
        "The statutory Explanation invoked by the authorities is absent from the supplied legal excerpt."
      ]
    },
    {
      "arrangement": 1,
      "condition": "DRC_BONA_FIDE-C02",
      "assessment": "UNRESOLVED",
      "evidence": [
        {
          "record": 1,
          "role": "CONTEXT",
          "connection": "Identifies the respondent as landlord but provides no residential-occupation requirement."
        },
        {
          "record": 3,
          "role": "CONTEXT",
          "connection": "The authorities addressed the premises' letting purpose and use, not the landlord's bona fide residential requirement."
        }
      ],
      "law_refs": ["IK-18143401:L41:historical-e"],
      "explanation": "The supplied record identifies the landlord and addresses residential letting and disputed commercial use. It provides no specific account establishing or disputing a bona fide requirement for residential occupation. Neither ownership nor residential letting alone establishes this proposition.",
      "gaps": [
        "No proposed residential need or supporting circumstances are supplied.",
        "The supplied law does not define bona fide or provide an operational standard."
      ]
    },
    {
      "arrangement": 1,
      "condition": "DRC_BONA_FIDE-C03/SELF",
      "assessment": "UNRESOLVED",
      "evidence": [
        {
          "record": 1,
          "role": "CONTEXT",
          "connection": "Identifies the respondent landlord without asserting that she intends to occupy the premises herself."
        }
      ],
      "law_refs": ["IK-18143401:L41:historical-e"],
      "explanation": "The respondent is identified as the successor landlord, but the materials do not say that she seeks to occupy the premises personally. Her acquisition of the property does not independently establish intended self-occupation.",
      "gaps": [
        "No affirmative or opposing account of the respondent's intended personal occupation is supplied."
      ]
    },
    {
      "arrangement": 1,
      "condition": "DRC_BONA_FIDE-C03/FAMILY",
      "assessment": "UNRESOLVED",
      "evidence": [
        {
          "record": 1,
          "role": "CONTEXT",
          "connection": "Identifies the respondent as the original landlord's daughter, but identifies no family member proposed to occupy the premises on her behalf."
        }
      ],
      "law_refs": ["IK-18143401:L41:historical-e"],
      "explanation": "The respondent's relationship to the former landlord establishes a family relationship but not an occupation proposal involving a member of the current landlord's family. No intended family occupant is identified.",
      "gaps": [
        "No family member proposed for residential occupation is identified."
      ]
    },
    {
      "arrangement": 1,
      "condition": "DRC_BONA_FIDE-C03/DEPENDENT",
      "assessment": "UNRESOLVED",
      "evidence": [
        {
          "record": 1,
          "role": "CONTEXT",
          "connection": "The respondent's status as daughter of the former landlord does not establish dependency of any proposed occupant on the current landlord."
        }
      ],
      "law_refs": ["IK-18143401:L41:historical-e"],
      "explanation": "No proposed family occupant or dependency relationship with the respondent landlord is established. The supplied family relationship cannot substitute for the distinct dependency requirement.",
      "gaps": [
        "No evidence of dependency on the current landlord is supplied.",
        "The supplied law does not define dependent."
      ]
    },
    {
      "arrangement": 1,
      "condition": "DRC_BONA_FIDE-C04",
      "assessment": "SUPPORTED",
      "evidence": [
        {
          "record": 1,
          "role": "SUPPORT",
          "connection": "The pre-target account expressly reports the respondent's purchase of the property from her father on 27th June, 1964 and succession as landlord."
        }
      ],
      "law_refs": ["IK-18143401:L41:historical-e"],
      "explanation": "The identified purchase of the same premises by the respondent supports her ownership in the landlord-or-dependent-family branch. The source supplies a specific transaction and date, although no conveyance instrument is independently available. This conclusion concerns ownership only, not the separate occupation requirement.",
      "gaps": [
        "The underlying purchase or conveyance instrument is not reproduced.",
        "No independent statutory definition or evidentiary test of ownership is supplied."
      ]
    },
    {
      "arrangement": 1,
      "condition": "DRC_BONA_FIDE-C05",
      "assessment": "UNRESOLVED",
      "evidence": [
        {
          "record": 1,
          "role": "CONTEXT",
          "connection": "Identifies a purchase by the respondent but does not identify another person for whose benefit the premises are held."
        }
      ],
      "law_refs": ["IK-18143401:L41:historical-e"],
      "explanation": "The record identifies the respondent as purchaser and landlord, but does not establish that the premises are held for a particular beneficiary whose residential occupation is proposed. The alternative statutory route therefore remains unresolved.",
      "gaps": [
        "No beneficiary or proposed occupation under this alternative route is identified."
      ]
    },
    {
      "arrangement": 1,
      "condition": "DRC_BONA_FIDE-C06",
      "assessment": "UNRESOLVED",
      "evidence": [],
      "law_refs": ["IK-18143401:L41:historical-e"],
      "explanation": "The supplied case accounts contain no evidence establishing either the absence or the existence of other reasonably suitable residential accommodation for the relevant statutory subject. Silence cannot establish the universal absence required by this proposition or refute it.",
      "gaps": [
        "No account of other residential accommodation or its suitability is supplied.",
        "The supplied law provides no operational suitability criteria and does not fully resolve the antecedent of such person."
      ]
    }
  ],
  "limitations": [
    {
      "arrangement": 1,
      "condition": "DRC_BONA_FIDE-C01",
      "records": [3, 4, 5, 6, 7, 8],
      "effect": "NOTE",
      "reason": "The statutory authorities' incidental-commercial-use finding conflicts with the High Court's evidentiary conclusion. Absence of documentary proof of boarding and lodging does not negate the tenant's account of foreign-student lodgers; rejection of sub-tenancy does not independently resolve commercial use. The legal effect of incidental commercial use cannot be fully assessed without the omitted statutory Explanation.",
      "refs": [
        "IK-1114159:L239:restored-v2",
        "IK-1114159:L240:span3",
        "IK-1114159:L241:span4",
        "IK-1114159:L244:restored-v2",
        "IK-18143401:L41:historical-e"
      ]
    },
    {
      "arrangement": 1,
      "condition": "DRC_BONA_FIDE-C04",
      "records": [1],
      "effect": "NOTE",
      "reason": "Ownership support comes from the specific pre-target case narrative of the purchase, not an independently inspected conveyance. The ownership assessment does not establish either occupation route or bona fide residential need.",
      "refs": [
        "IK-1114159:L238:restored-v2",
        "IK-18143401:L41:historical-e"
      ]
    }
  ],
  "coverage_limits": [
    "The analysis uses only the supplied case accounts and clause (e) excerpt. The excerpt ends with Explanation. but does not provide its text; no missing rule is inferred.",
    "The Rent Note, letters, conveyance and underlying evidentiary materials are not reproduced. Prior judicial findings retain their respective stages, and Supreme Court acceptance is not presumed.",
    "No supplied evidence resolves the proposed residential occupant, bona fide requirement, dependent-family route, beneficiary route or absence of other reasonably suitable accommodation.",
    "The supplied law does not establish an evidentiary burden, standard of proof, independent defense, or detailed interpretive criteria. No final request outcome is assessed."
  ]
}
```

## 52547606 P

[Raw](runs/52547606/P/raw-response.txt) · [Parsed](runs/52547606/P/parsed.json) · [Submitted task](runs/52547606/P/submitted-task.txt) · [Conversation](https://chatgpt.com/c/6ac86c5f-5f88-83e8-892d-df984c324fd1?temporary-chat=true)

```json
{
  "records": [
    {
      "text": "The landlord's contention at the pre-target stage was that tenant Mohan Lal sublet the disputed premises to Anand Parkash and others, including 'Parkash Trading Corporation' through Ram Parkash.",
      "statement_status": "PARTY_CLAIM",
      "refs": ["IK-52547606:L74:span1"]
    },
    {
      "text": "The tenant denied subletting, asserting that Mohan Lal rented the premises for his son Anand Parkash's business with the consent and knowledge of the landlord, who lived in the same premises.",
      "statement_status": "DENIAL",
      "refs": ["IK-52547606:L75:span2"]
    },
    {
      "text": "AW-4 proved an electricity connection in Mohan Lal's name and a rent receipt in his favour.",
      "statement_status": "TESTIMONY",
      "refs": ["IK-52547606:L78:span3"]
    },
    {
      "text": "AW-5 proved telephone records showing that M/s Parkash Trading Corporation maintained a telephone at the disputed premises until 21.05.1963; the firm subsequently dissolved and the telephone was shifted.",
      "statement_status": "TESTIMONY",
      "refs": ["IK-52547606:L79:span4"]
    },
    {
      "text": "The proved partnership deed Ex. RW-5/X13 identified Anand Parkash as a partner in M/s Parkash Trading Corporation. Following the firm's dissolution, another partnership deed, Ex.RW-5/X15, was executed.",
      "statement_status": "RECORDED_DOCUMENT",
      "refs": ["IK-52547606:L81:span5"]
    },
    {
      "text": "The ARC found that deceased Mohan Lal was the tenant and that Anand Parkash had operated his business at the premises from the beginning, as admitted by the landlord. The ARC found no basis to infer subletting, assignment or parting with possession by Mohan Lal in favour of Anand Parkash.",
      "statement_status": "PRIOR_COURT_FINDING",
      "refs": ["IK-52547606:L82:context-v4"]
    },
    {
      "text": "The ARCT found that Mohan Lal was the tenant but had parted with possession in favour of his son Anand Parkash, who conducted business at the premises. It confirmed the Section 14(1)(b) subletting ground in favour of the landlord.",
      "statement_status": "PRIOR_COURT_FINDING",
      "refs": ["IK-52547606:L84:context-v4"]
    },
    {
      "text": "Landlord Maheshwar Dayal, examined as AW-7, admitted in cross-examination that Mohan Lal took the premises for Anand Parkash's business and that Anand Parkash used them from the inception of the tenancy.",
      "statement_status": "ADMISSION",
      "refs": ["IK-52547606:L93:span8"]
    }
  ],
  "arrangements": [
    {
      "description": "Mohan Lal's tenancy of the disputed premises and the ongoing business use by his son Anand Parkash from the tenancy's inception. The tenant asserted landlord consent, and landlord Maheshwar Dayal admitted the original business purpose and use. Whether Mohan Lal transferred possession or tenancy rights to Anand Parkash is disputed, with conflicting ARC and ARCT findings.",
      "refs": [
        "IK-52547606:L74:span1",
        "IK-52547606:L75:span2",
        "IK-52547606:L78:span3",
        "IK-52547606:L82:context-v4",
        "IK-52547606:L84:context-v4",
        "IK-52547606:L93:span8"
      ]
    },
    {
      "description": "Reported use of the disputed premises by M/s Parkash Trading Corporation, allegedly through Ram Parkash, with Anand Parkash identified as a partner. The firm maintained a telephone there until 21.05.1963 and subsequently dissolved. This firm-linked activity may overlap Anand Parkash's business use; whether it constituted a distinct disposition by Mohan Lal is not established.",
      "refs": [
        "IK-52547606:L74:span1",
        "IK-52547606:L79:span4",
        "IK-52547606:L81:span5",
        "IK-52547606:L93:span8"
      ]
    }
  ],
  "conditions": [
    {
      "arrangement": 1,
      "condition": "DRC_SUBLETTING_C01",
      "assessment": "UNRESOLVED",
      "evidence": [
        {
          "record": 2,
          "role": "CONTEXT",
          "connection": "Describes the tenancy's original purpose without identifying its commencement date."
        },
        {
          "record": 8,
          "role": "CONTEXT",
          "connection": "Confirms Anand Parkash's use from inception but supplies no calendar date for any disposition."
        }
      ],
      "law_refs": ["LAW:S02:DRC14:1b"],
      "explanation": "The evidence establishes use from the beginning of the tenancy, but neither the tenancy's commencement date nor the date of an alleged disposition to Anand Parkash is supplied. The statutory cutoff cannot be applied merely from the existence of business use.",
      "gaps": [
        "Tenancy commencement date is unspecified.",
        "No date of a qualifying disposition to Anand Parkash is established."
      ]
    },
    {
      "arrangement": 1,
      "condition": "DRC_SUBLETTING_C02",
      "assessment": "UNRESOLVED",
      "evidence": [
        {
          "record": 1,
          "role": "SUPPORT",
          "connection": "Expressly alleges subletting to Anand Parkash."
        },
        {
          "record": 2,
          "role": "OPPOSE",
          "connection": "Denies subletting and describes intended business use by the tenant's son."
        },
        {
          "record": 6,
          "role": "OPPOSE",
          "connection": "The ARC rejected an inference of subletting from the evidence."
        },
        {
          "record": 7,
          "role": "CONTEXT",
          "connection": "The ARCT confirmed the statutory ground through a finding of parting with possession, without separately identifying every required subtenancy incident."
        },
        {
          "record": 8,
          "role": "CONTEXT",
          "connection": "The landlord admitted Anand Parkash's original business use, not a separate tenancy relationship."
        }
      ],
      "law_refs": [
        "IK-190902:L109",
        "IK-190902:L110"
      ],
      "explanation": "The subletting allegation and the ARCT's statutory-ground conclusion are relevant, but the supplied findings distinguish poorly between subletting and parting with possession. No specific evidence establishes rent payable by Anand Parkash to Mohan Lal, transfer of an estate interest, and a right to possession against Mohan Lal within the same subtenancy. The tenant's denial and the ARC's contrary finding remain material.",
      "gaps": [
        "No identified subtenancy rent or transfer instrument.",
        "No separate finding establishing every required subletting incident."
      ]
    },
    {
      "arrangement": 1,
      "condition": "DRC_SUBLETTING_C04",
      "assessment": "UNRESOLVED",
      "evidence": [
        {
          "record": 7,
          "role": "SUPPORT",
          "connection": "The ARCT expressly found that Mohan Lal parted with possession in favour of Anand Parkash."
        },
        {
          "record": 6,
          "role": "OPPOSE",
          "connection": "The ARC concluded that parting with possession could not be inferred."
        },
        {
          "record": 2,
          "role": "OPPOSE",
          "connection": "The tenant characterized Anand Parkash's use as the intended business arrangement from inception."
        },
        {
          "record": 8,
          "role": "CONTEXT",
          "connection": "Confirms original business use without directly resolving divestment of legal possession."
        },
        {
          "record": 3,
          "role": "CONTEXT",
          "connection": "Documents remained in Mohan Lal's name, relevant to tenancy identity but not conclusive of retained possession."
        }
      ],
      "law_refs": [
        "IK-190902:L107",
        "IK-190902:L111",
        "IK-190902:L112"
      ],
      "explanation": "The ARCT's affirmative parting-with-possession finding directly supports the proposition, while the ARC expressly reached the opposite inference from the evidence. The landlord's admission establishes Anand Parkash's use from inception but does not itself show that Mohan Lal surrendered physical possession and the right to possession. Target-court acceptance of either interpretation is not supplied.",
      "gaps": [
        "The precise allocation of legal possession between Mohan Lal and Anand Parkash is disputed.",
        "The conflicting prior findings have no supplied target-stage resolution."
      ]
    },
    {
      "arrangement": 1,
      "condition": "DRC_SUBLETTING_C05",
      "assessment": "UNRESOLVED",
      "evidence": [
        {
          "record": 2,
          "role": "OPPOSE",
          "connection": "The tenant asserted landlord consent but did not specify written consent."
        },
        {
          "record": 8,
          "role": "CONTEXT",
          "connection": "The landlord admitted knowledge of the original business purpose and use, without addressing a written consent instrument."
        }
      ],
      "law_refs": ["LAW:S02:DRC14:1b"],
      "explanation": "The tenant asserted consent and the landlord acknowledged the original arrangement, but neither statement establishes written consent for a legally relevant disposition. Equally, the absence of a supplied written instrument does not prove that written consent was never obtained. The complete negative proposition remains unresolved.",
      "gaps": [
        "No written consent instrument or express finding of its absence is supplied.",
        "The scope and form of the alleged consent are unspecified."
      ]
    },
    {
      "arrangement": 1,
      "condition": "DRC_SUBLETTING_C06",
      "assessment": "UNRESOLVED",
      "evidence": [
        {
          "record": 2,
          "role": "SUPPORT",
          "connection": "Describes the son's business use as the tenancy's intended arrangement rather than a later surrender."
        },
        {
          "record": 3,
          "role": "SUPPORT",
          "connection": "The electricity connection and rent receipt name Mohan Lal, supporting continuing tenancy identity without conclusively establishing legal possession."
        },
        {
          "record": 6,
          "role": "SUPPORT",
          "connection": "The ARC found no inference of parting with possession despite Anand Parkash's business use."
        },
        {
          "record": 8,
          "role": "SUPPORT",
          "connection": "The landlord's admission corroborates the son's use from the start."
        },
        {
          "record": 7,
          "role": "OPPOSE",
          "connection": "The ARCT nevertheless concluded that Mohan Lal parted with possession."
        }
      ],
      "law_refs": [
        "IK-190902:L107",
        "IK-190902:L112"
      ],
      "explanation": "The original business purpose, documentary tenancy identity, and ARC finding support a retained-possession interpretation. The contrary ARCT finding is substantial opposition. Neither the documents nor the admitted business use conclusively establish concurrent legal possession or absence of complete ouster, and this qualification applies only to the parting-with-possession route.",
      "gaps": [
        "No definitive finding establishes whether Mohan Lal retained the right to possess the relevant part.",
        "The terms of any concurrent-use arrangement are unspecified."
      ]
    },
    {
      "arrangement": 1,
      "condition": "DRC_SUBLETTING_C07",
      "assessment": "SUPPORTED",
      "evidence": [
        {
          "record": 1,
          "role": "SUPPORT",
          "connection": "The allegation concerns the disputed rented premises."
        },
        {
          "record": 7,
          "role": "SUPPORT",
          "connection": "The ARCT's finding identifies the premises whose possession was allegedly transferred to Anand Parkash."
        },
        {
          "record": 8,
          "role": "SUPPORT",
          "connection": "Identifies Anand Parkash's business use as occurring at those premises."
        },
        {
          "record": 6,
          "role": "CONTEXT",
          "connection": "The ARC disputed the existence of a qualifying disposition, not the identity of the premises used."
        }
      ],
      "law_refs": ["LAW:S02:DRC14:1b"],
      "explanation": "The alleged disposition and the ARCT's recorded finding concern the disputed rented premises used by Anand Parkash. This supports the premises-scope identification without independently establishing that a legally qualifying disposition occurred or determining its precise extent.",
      "gaps": [
        "The exact physical extent of any transferred possession remains unspecified."
      ]
    },
    {
      "arrangement": 2,
      "condition": "DRC_SUBLETTING_C01",
      "assessment": "UNRESOLVED",
      "evidence": [
        {
          "record": 4,
          "role": "CONTEXT",
          "connection": "Establishes reported telephone use until 21.05.1963, not the commencement of any subletting or possession transfer."
        },
        {
          "record": 5,
          "role": "CONTEXT",
          "connection": "Establishes a partnership and subsequent dissolution without dating a disposition by Mohan Lal."
        },
        {
          "record": 1,
          "role": "SUPPORT",
          "connection": "Alleges a disposition involving the firm but supplies no transaction date."
        }
      ],
      "law_refs": ["LAW:S02:DRC14:1b"],
      "explanation": "The telephone record supports the firm's presence at the premises through a date after the statutory cutoff. It does not establish when, or whether, Mohan Lal made a qualifying disposition to the firm. The partnership documents do not resolve that temporal question.",
      "gaps": [
        "No dated transaction of subletting, assignment or parting with possession to the firm is identified."
      ]
    },
    {
      "arrangement": 2,
      "condition": "DRC_SUBLETTING_C02",
      "assessment": "UNRESOLVED",
      "evidence": [
        {
          "record": 1,
          "role": "SUPPORT",
          "connection": "Alleges subletting to 'Parkash Trading Corporation' through Ram Parkash."
        },
        {
          "record": 4,
          "role": "CONTEXT",
          "connection": "The telephone record corroborates firm-linked use of the premises, not subtenancy incidents."
        },
        {
          "record": 5,
          "role": "CONTEXT",
          "connection": "Proves Anand Parkash's partnership connection, not a landlord-and-tenant relationship between Mohan Lal and the firm."
        },
        {
          "record": 6,
          "role": "UNRESOLVED",
          "connection": "The ARC's recorded rejection concerns disposition in favour of Anand Parkash and does not separately determine a firm subtenancy."
        },
        {
          "record": 7,
          "role": "UNRESOLVED",
          "connection": "The ARCT found parting with possession in favour of Anand Parkash, without separately determining a firm subtenancy."
        }
      ],
      "law_refs": [
        "IK-190902:L109",
        "IK-190902:L110"
      ],
      "explanation": "The allegation, telephone records and partnership deed support the firm's connection with the premises. They do not establish payment of rent to Mohan Lal, transfer of an estate interest, or the firm's right to possession against Mohan Lal as incidents of the same subtenancy. Findings about Anand Parkash cannot automatically establish a distinct subletting to the firm.",
      "gaps": [
        "No firm-specific rent, subtenancy instrument or possession right is established.",
        "The relationship between the firm's use and Anand Parkash's original business arrangement remains uncertain."
      ]
    },
    {
      "arrangement": 2,
      "condition": "DRC_SUBLETTING_C04",
      "assessment": "UNRESOLVED",
      "evidence": [
        {
          "record": 1,
          "role": "SUPPORT",
          "connection": "Alleges a disposition involving the firm through Ram Parkash."
        },
        {
          "record": 4,
          "role": "CONTEXT",
          "connection": "Corroborates the firm's telephone presence without proving divestment of Mohan Lal's right to possession."
        },
        {
          "record": 5,
          "role": "CONTEXT",
          "connection": "Establishes partnership arrangements without establishing a transfer of possession by Mohan Lal."
        },
        {
          "record": 7,
          "role": "UNRESOLVED",
          "connection": "The ARCT's express finding concerns transfer to Anand Parkash and does not independently establish transfer to the firm."
        }
      ],
      "law_refs": [
        "IK-190902:L107",
        "IK-190902:L111",
        "IK-190902:L112"
      ],
      "explanation": "Firm-linked occupation or use and partnership membership do not independently demonstrate that Mohan Lal vested physical possession and the right to possession in the firm. The ARCT's finding concerning Anand Parkash may involve overlapping business activity, but a separate firm-directed disposition cannot be inferred from shared persons and premises alone.",
      "gaps": [
        "No firm-specific vesting or surrender of legal possession is established.",
        "Whether the firm's use was distinct from Anand Parkash's use is unresolved."
      ]
    },
    {
      "arrangement": 2,
      "condition": "DRC_SUBLETTING_C05",
      "assessment": "UNRESOLVED",
      "evidence": [
        {
          "record": 2,
          "role": "UNRESOLVED",
          "connection": "The asserted landlord consent concerns Anand Parkash's business; its applicability to a separate firm disposition is unknown."
        },
        {
          "record": 8,
          "role": "CONTEXT",
          "connection": "The landlord admitted the son's original business use, not written consent to a firm-specific disposition."
        },
        {
          "record": 1,
          "role": "CONTEXT",
          "connection": "The allegation identifies the firm but does not establish the presence or absence of written consent."
        }
      ],
      "law_refs": ["LAW:S02:DRC14:1b"],
      "explanation": "Consent concerning the son's original business purpose cannot automatically be extended to a legally distinct disposition to M/s Parkash Trading Corporation. The supplied evidence contains neither a firm-specific written consent instrument nor an express finding that such consent was absent.",
      "gaps": [
        "The existence and scope of any written consent covering the firm's alleged disposition are unknown."
      ]
    }
  ],
  "limitations": [
    {
      "arrangement": 1,
      "condition": "DRC_SUBLETTING_C04",
      "records": [6, 7],
      "effect": "NOTE",
      "reason": "The ARC and ARCT reached opposing findings about the same proposed transfer to Anand Parkash. Both are prior-stage findings; neither constitutes supplied acceptance by the target Delhi High Court.",
      "refs": [
        "IK-52547606:L82:context-v4",
        "IK-52547606:L84:context-v4"
      ]
    },
    {
      "arrangement": 2,
      "condition": "DRC_SUBLETTING_C01",
      "records": [4],
      "effect": "NOTE",
      "reason": "The telephone record's endpoint of 21.05.1963 cannot be treated as the date of a qualifying disposition or as proof that such a disposition occurred after 9 June 1952.",
      "refs": [
        "IK-52547606:L79:span4",
        "LAW:S02:DRC14:1b"
      ]
    },
    {
      "arrangement": 1,
      "condition": "DRC_SUBLETTING_C05",
      "records": [],
      "effect": "CONDITION_PENDING",
      "reason": "The record identifies asserted landlord consent and admitted knowledge but does not establish whether written consent existed for the relevant disposition. Neither absence of a supplied instrument nor general knowledge resolves the statutory requirement.",
      "refs": [
        "IK-52547606:L75:span2",
        "IK-52547606:L93:span8",
        "LAW:S02:DRC14:1b"
      ]
    },
    {
      "arrangement": 2,
      "condition": "DRC_SUBLETTING_C04",
      "records": [],
      "effect": "CONDITION_PENDING",
      "reason": "The supplied record does not establish whether the firm received independent legal possession from Mohan Lal or merely participated in Anand Parkash's business use. The findings directed at Anand Parkash do not conclusively resolve that correspondence.",
      "refs": [
        "IK-52547606:L74:span1",
        "IK-52547606:L79:span4",
        "IK-52547606:L81:span5",
        "IK-52547606:L84:context-v4"
      ]
    }
  ],
  "coverage_limits": [
    "The ARC and ARCT findings are preserved as distinct prior-stage conclusions. The supplied materials do not establish their acceptance or rejection by the target Delhi High Court.",
    "The date of any qualifying disposition, the presence or absence of written landlord consent, and the precise allocation of legal possession remain unresolved.",
    "The firm's recorded activity does not independently establish a distinct disposition, and the supplied evidence does not establish assignment through divestment of all tenancy rights. No separate assignment-route judgment is made.",
    "Only the supplied statutory and interpretive excerpts are used. No burden allocation, proof standard, evidentiary presumption, or final request outcome is inferred."
  ]
}
```

## 55384096 P

[Raw](runs/55384096/P/raw-response.txt) · [Parsed](runs/55384096/P/parsed.json) · [Submitted task](runs/55384096/P/submitted-task.txt) · [Conversation](https://chatgpt.com/c/6ac86e1d-173c-83e8-9434-8f93a6d4641e?temporary-chat=true)

```json
{
  "records": [
    {
      "text": "At the pre-target stage, the petitioner alleged that Hakim Rai, the original tenant of the ground-floor shop at property no.95, Main Bazar, Najafgarh, Delhi, had sublet it to his son-in-law Raj Kumar and completely divested himself of the suit property.",
      "statement_status": "PARTY_CLAIM",
      "refs": ["IK-55384096:L67:span1"]
    },
    {
      "text": "In his pre-target defence, Hakim Rai stated that he was elderly, ailing, and losing his eyesight, and that he had requested Raj Kumar to assist with his business during the latter part of 1983.",
      "statement_status": "PARTY_CLAIM",
      "refs": ["IK-55384096:L69:span2"]
    },
    {
      "text": "The pre-target case narrative reports a partnership deed dated 20.11.1983, Ex.AW-3/13, between Hakim Rai and Raj Kumar, providing that their partnership business would operate from the suit premises. The reported instrument's authenticity remains disputed.",
      "statement_status": "RECORDED_DOCUMENT",
      "refs": ["IK-55384096:L70:span3"]
    },
    {
      "text": "At the pre-target stage, the landlord contended that Ex.AW-3/13 was fake and forged, created as a sham defence to the eviction petition under Section 14(1)(b).",
      "statement_status": "PARTY_CLAIM",
      "refs": ["IK-55384096:L71:span4"]
    },
    {
      "text": "RW-1 Sumitra Devi, Hakim Rai's widow, testified that her husband initially operated the shop, she also participated in its business, and Raj Kumar was her husband's business partner. She denied that Hakim Rai had ceased possessing or conducting business after Raj Kumar's induction. She did not know whether Hakim Rai had deposited rent and testified that he became blind approximately one and a half years before his death.",
      "statement_status": "TESTIMONY",
      "refs": [
        "IK-55384096:L76:context-v4",
        "IK-55384096:L77:context-v4",
        "IK-55384096:L77:span5",
        "IK-55384096:L77:span6"
      ]
    },
    {
      "text": "The pre-target case narrative states that Hakim Rai and Raj Kumar resided at the same premises and Raj Kumar had obtained a ration card at that address. It also identifies execution of their partnership deed in November 1983. The residential address is not independently established as identical to the demised shop.",
      "statement_status": "UNKNOWN",
      "refs": ["IK-55384096:L79:span7"]
    },
    {
      "text": "PW-3, the landlord's attorney, admitted that Hakim Rai was elderly, had very poor eyesight, and could not walk properly.",
      "statement_status": "ADMISSION",
      "refs": ["IK-55384096:L80:span8"]
    }
  ],
  "arrangements": [
    {
      "description": "The disputed arrangement concerns the ground-floor shop at property no.95, Main Bazar, Najafgarh, Delhi, originally let to Hakim Rai. Raj Kumar, Hakim Rai's son-in-law, became involved in the shop business, which the defence associated with assistance requested in late 1983 and the reported partnership deed dated 20.11.1983. The landlord characterizes the same involvement as subletting accompanied by complete divestment, and challenges the partnership deed's authenticity. The actual contractual relationship, control, and legal possession remain contested. Shared residence is contextual and does not independently establish another disposition of the shop.",
      "refs": [
        "IK-55384096:L67:span1",
        "IK-55384096:L69:span2",
        "IK-55384096:L70:span3",
        "IK-55384096:L71:span4",
        "IK-55384096:L77:context-v4",
        "IK-55384096:L79:span7"
      ]
    }
  ],
  "conditions": [
    {
      "arrangement": 1,
      "condition": "DRC_SUBLETTING_C01",
      "assessment": "UNRESOLVED",
      "evidence": [
        {
          "record": 1,
          "role": "UNRESOLVED",
          "connection": "Alleges subletting but does not identify its occurrence date."
        },
        {
          "record": 2,
          "role": "CONTEXT",
          "connection": "Places the request for Raj Kumar's assistance in late 1983, not a proved disposition."
        },
        {
          "record": 3,
          "role": "CONTEXT",
          "connection": "Identifies a partnership deed dated 20.11.1983 without establishing that a statutory disposition occurred on that date."
        }
      ],
      "law_refs": ["LAW:S02:DRC14:1b"],
      "explanation": "The reported involvement of Raj Kumar and partnership documentation date from 1983, after the statutory threshold. However, an assistance request or partnership deed is not independently proof that subletting, assignment, or parting with possession occurred. The date of a qualifying disposition therefore remains unresolved.",
      "gaps": [
        "The occurrence and date of the alleged statutory disposition are unestablished.",
        "The materials do not explain how any continuing arrangement should be dated."
      ]
    },
    {
      "arrangement": 1,
      "condition": "DRC_SUBLETTING_C02",
      "assessment": "UNRESOLVED",
      "evidence": [
        {
          "record": 1,
          "role": "SUPPORT",
          "connection": "Expressly alleges subletting to Raj Kumar but supplies no particular tenancy incidents."
        },
        {
          "record": 3,
          "role": "OPPOSE",
          "connection": "Describes a partnership business rather than a subtenancy, although the deed's authenticity and legal effect are disputed."
        },
        {
          "record": 4,
          "role": "CONTEXT",
          "connection": "Challenges the genuineness of the partnership explanation without independently proving tenancy incidents."
        },
        {
          "record": 5,
          "role": "OPPOSE",
          "connection": "Testifies to a business partnership and Hakim Rai's continued involvement, contrary to the asserted substitution of Raj Kumar as subtenant."
        }
      ],
      "law_refs": [
        "IK-190902:L109",
        "IK-190902:L110"
      ],
      "explanation": "The landlord alleges subletting, whereas the reported deed and Sumitra Devi's testimony describe a business partnership. The landlord contests the deed, and the supplied record does not establish a transfer of an estate interest, rent paid by Raj Kumar to Hakim Rai, or Raj Kumar's right to possession against Hakim Rai. Sumitra Devi's uncertainty about Hakim Rai depositing rent concerns a different payment question. Neither the complete subletting proposition nor its negation is established.",
      "gaps": [
        "No established transfer of tenancy interest or right to possession against Hakim Rai.",
        "No established rent arrangement between Hakim Rai and Raj Kumar.",
        "Partnership deed authenticity and legal effect remain contested."
      ]
    },
    {
      "arrangement": 1,
      "condition": "DRC_SUBLETTING_C03",
      "assessment": "UNRESOLVED",
      "evidence": [
        {
          "record": 1,
          "role": "SUPPORT",
          "connection": "Alleges complete divestment, potentially relevant to assignment, without identifying a transfer of all tenancy rights."
        },
        {
          "record": 3,
          "role": "OPPOSE",
          "connection": "The reported joint partnership is inconsistent with an uncomplicated account of complete withdrawal, but does not conclusively establish retained tenancy rights."
        },
        {
          "record": 4,
          "role": "CONTEXT",
          "connection": "Disputes the authenticity of the document relied upon for the alternative arrangement."
        },
        {
          "record": 5,
          "role": "OPPOSE",
          "connection": "Testifies that Hakim Rai continued in possession and business after Raj Kumar's induction."
        }
      ],
      "law_refs": ["IK-190902:L110"],
      "explanation": "The landlord's complete-divestment allegation provides relevant support, but the defence material and widow's testimony oppose it. The supplied material does not identify an assignment instrument or establish that Hakim Rai surrendered every right held as tenant. Business involvement is not automatically equivalent to the retention or assignment of all tenancy rights.",
      "gaps": [
        "No established transfer or surrender of all tenancy rights.",
        "The competing accounts of continued participation and complete divestment remain unresolved."
      ]
    },
    {
      "arrangement": 1,
      "condition": "DRC_SUBLETTING_C04",
      "assessment": "UNRESOLVED",
      "evidence": [
        {
          "record": 1,
          "role": "SUPPORT",
          "connection": "Alleges complete divestment of the suit property in favour of Raj Kumar."
        },
        {
          "record": 2,
          "role": "OPPOSE",
          "connection": "Describes Raj Kumar's entry as assistance with Hakim Rai's business rather than a transfer of possession."
        },
        {
          "record": 3,
          "role": "OPPOSE",
          "connection": "Reports a joint business arrangement inconsistent with the alleged complete exclusion, subject to the authenticity dispute."
        },
        {
          "record": 4,
          "role": "CONTEXT",
          "connection": "Attacks the partnership explanation without separately establishing divestment of legal possession."
        },
        {
          "record": 5,
          "role": "OPPOSE",
          "connection": "Expressly denies Hakim Rai's loss of possession after Raj Kumar's induction."
        },
        {
          "record": 7,
          "role": "CONTEXT",
          "connection": "Corroborates physical limitations that could explain assistance but does not determine legal possession."
        }
      ],
      "law_refs": [
        "IK-190902:L107",
        "IK-190902:L111",
        "IK-190902:L112"
      ],
      "explanation": "The landlord alleges complete divestment, directly opposed by the widow's testimony and the defence account of assistance and partnership. PW-3 corroborates Hakim Rai's physical limitations, not a transfer of possession. The supplied legal rule requires tenant-caused vesting of possession in another person and divestment of the tenant's physical possession and right to possession. Those legal and factual requirements are not conclusively established or negated by the competing accounts.",
      "gaps": [
        "No established agreement transferring legal possession or the right to possession.",
        "Actual control and any continuing entitlement of Hakim Rai remain disputed.",
        "The reported partnership instrument's authenticity is contested."
      ]
    },
    {
      "arrangement": 1,
      "condition": "DRC_SUBLETTING_C05",
      "assessment": "UNRESOLVED",
      "evidence": [],
      "law_refs": ["LAW:S02:DRC14:1b"],
      "explanation": "The supplied case passages do not address whether the landlord provided written consent for the alleged disposition. The absence of a consent document from these excerpts does not establish that consent was never obtained. Neither written consent nor its absence can be determined from the supplied materials.",
      "gaps": [
        "No supplied consent instrument, specific denial of written consent, or finding about consent.",
        "No supplied burden allocation or evidentiary presumption governing written consent."
      ]
    },
    {
      "arrangement": 1,
      "condition": "DRC_SUBLETTING_C06",
      "assessment": "UNRESOLVED",
      "evidence": [
        {
          "record": 1,
          "role": "OPPOSE",
          "connection": "Alleges that Hakim Rai completely divested himself of the suit property."
        },
        {
          "record": 2,
          "role": "SUPPORT",
          "connection": "Describes assistance requested by the tenant rather than an express surrender of possession."
        },
        {
          "record": 3,
          "role": "SUPPORT",
          "connection": "Reports a joint partnership operating from the shop, consistent with possible concurrent use but not decisive of legal possession."
        },
        {
          "record": 4,
          "role": "OPPOSE",
          "connection": "Disputes the genuineness of the partnership instrument relied upon to explain joint occupation."
        },
        {
          "record": 5,
          "role": "SUPPORT",
          "connection": "Testifies to Hakim Rai's continued possession and business participation after Raj Kumar joined."
        },
        {
          "record": 7,
          "role": "CONTEXT",
          "connection": "Supports the explanation for seeking assistance without establishing a continuing legal right to possession."
        }
      ],
      "law_refs": [
        "IK-190902:L107",
        "IK-190902:L112"
      ],
      "explanation": "Sumitra Devi's testimony and the reported partnership provide particular support for continued involvement and potentially concurrent use. They are opposed by the landlord's complete-divestment allegation and challenge to the deed. Continued business participation alone does not conclusively establish retained legal possession of the relevant shop or part. Because the opposing accounts remain unresolved, the complete retained-possession proposition cannot be accepted or rejected.",
      "gaps": [
        "The actual right to legal possession and any exclusive right conferred upon Raj Kumar remain unestablished.",
        "The precise area, control arrangements, and possible ouster are not independently established."
      ]
    },
    {
      "arrangement": 1,
      "condition": "DRC_SUBLETTING_C07",
      "assessment": "SUPPORTED",
      "evidence": [
        {
          "record": 1,
          "role": "SUPPORT",
          "connection": "Identifies the alleged subletting and divestment as concerning the originally let ground-floor shop."
        },
        {
          "record": 3,
          "role": "SUPPORT",
          "connection": "Identifies the suit premises as the location of the reported partnership business."
        },
        {
          "record": 5,
          "role": "SUPPORT",
          "connection": "Describes the business activities and Raj Kumar's participation in the demised shop."
        }
      ],
      "law_refs": ["LAW:S02:DRC14:1b"],
      "explanation": "The alleged disposition and the competing partnership explanation concern the same identified demised shop. This supports the premises-scope connection required by the proposition. It does not independently establish that a legally qualifying disposition occurred or determine its precise extent.",
      "gaps": [
        "The particular portion, if less than the whole shop, has not been separately identified.",
        "The legal character and actual occurrence of the alleged disposition remain disputed."
      ]
    }
  ],
  "limitations": [
    {
      "arrangement": 1,
      "condition": "DRC_SUBLETTING_C01",
      "records": [3],
      "effect": "NOTE",
      "reason": "The deed's date is identifiable, but its execution date must not automatically be treated as the date of subletting, assignment, or parting with possession.",
      "refs": [
        "IK-55384096:L70:span3",
        "LAW:S02:DRC14:1b"
      ]
    },
    {
      "arrangement": 1,
      "condition": "DRC_SUBLETTING_C02",
      "records": [3],
      "effect": "NOTE",
      "reason": "The case narrative reports the partnership instrument, but the landlord alleges forgery and fabrication. Its authenticity and effect cannot be treated as conclusively established.",
      "refs": [
        "IK-55384096:L70:span3",
        "IK-55384096:L71:span4"
      ]
    },
    {
      "arrangement": 1,
      "condition": "DRC_SUBLETTING_C05",
      "records": [],
      "effect": "CONDITION_PENDING",
      "reason": "No supplied case account establishes whether the landlord's written consent was obtained for the same alleged disposition. This proposition cannot be decided from silence.",
      "refs": [
        "IK-55384096:L67:span1",
        "LAW:S02:DRC14:1b"
      ]
    }
  ],
  "coverage_limits": [
    "The supplied case excerpts contain allegations, a defence account, a reported instrument, testimony, an admission, and contextual facts. They do not supply an explicit adjudicated finding resolving the contested disposition or authenticity issues, nor the target High Court's acceptance of those accounts.",
    "The supplied legal structure distinguishes subletting, assignment, and parting with possession. It provides no additional burden allocation, proof standard, presumption concerning missing evidence, or supplementary written-consent doctrine.",
    "The reported November 1983 partnership, alleged transfer of possession, and residential co-address must not be conflated. The residence and ration-card details do not independently prove occupation, transfer, or exclusive legal possession of the demised shop.",
    "These assessments organize the single disputed shop arrangement retrospectively from the supplied materials. They do not predict the request outcome or reconstruct an excluded target judgment."
  ]
}
```

## 68065690 P

[Raw](runs/68065690/P/raw-response.txt) · [Parsed](runs/68065690/P/parsed.json) · [Submitted task](runs/68065690/P/submitted-task.txt) · [Conversation](https://chatgpt.com/c/6ac870bb-419c-83e8-9e6f-b415a40de7e1?temporary-chat=true)

```json
{
  "records": [
    {
      "text": "At the pre-target pleading stage, the petitioner alleges that the respondent sublet the disputed shop to Shri Kapil Luthra, son of Shri Veer Bhan, for Rs.5500/- per month without the petitioner's knowledge, consent or permission. The petitioner further alleges that Kapil Luthra uses the shop as a godown and has taken exclusive possession.",
      "statement_status": "PARTY_CLAIM",
      "refs": [
        "IK-68065690:L76:span1"
      ]
    },
    {
      "text": "An unattributed pre-target passage states that the shop is used as a godown for storing spare parts and cycles and that the petitioner knows this. The excerpt does not independently identify its speaker.",
      "statement_status": "UNKNOWN",
      "refs": [
        "IK-68065690:L80:span2"
      ]
    },
    {
      "text": "At the pre-target pleading stage, the respondent denies subletting the disputed shop to Sh. Kapil Luthra for Rs.5500/- per month, denies Kapil Luthra's alleged godown use and exclusive possession, and denies ever subletting or assigning the shop to him.",
      "statement_status": "DENIAL",
      "refs": [
        "IK-68065690:L82:span3",
        "IK-68065690:L83:span4"
      ]
    },
    {
      "text": "At the pre-target pleading stage, the respondent claims to operate a cycle works shop at Shop No. 29/5, Shakti Nagar, Delhi-07, while using the disputed shop as his own godown. He describes Kapil Luthra as merely helping with the family business and states that no rent is received from him.",
      "statement_status": "PARTY_CLAIM",
      "refs": [
        "IK-68065690:L83:span4",
        "IK-68065690:L84:span5"
      ]
    },
    {
      "text": "The recorded account of the respondent's reply dated 17 September 2009 to a legal notice reports his assertion that Kapil Luthra is his nephew, helps in the family business, and that his family remains in possession of the shop as lawful tenant. This is a reported documentary assertion, not an independently established possession finding.",
      "statement_status": "RECORDED_DOCUMENT",
      "refs": [
        "IK-68065690:L174:context-v4"
      ]
    },
    {
      "text": "In pre-target testimony, RW1, the respondent, describes an oral partnership involving Veer Bhan Luthra and Kapil Luthra. He states that no partnership deed was executed, no partnership accounts were maintained, Veer Bhan was principally responsible, and the partnership had existed since 1975.",
      "statement_status": "TESTIMONY",
      "refs": [
        "IK-68065690:L176:context-v4"
      ]
    },
    {
      "text": "During pre-target cross-examination, RW2, Sh. Kapil Luthra, testifies that he conducts business as Luthra Cycle Stores from the disputed premises and has no other shop or business.",
      "statement_status": "TESTIMONY",
      "refs": [
        "IK-68065690:L181:context-v4"
      ]
    }
  ],
  "arrangements": [
    {
      "description": "The disputed rented shop involves the respondent as tenant and Kapil Luthra as the alleged subtenant or occupant. The petitioner alleges a Rs.5500/- monthly subletting and exclusive possession by Kapil Luthra. The respondent instead describes his own godown use, family-business assistance without rent, and continued family possession. RW1 describes an oral partnership involving Veer Bhan Luthra and Kapil Luthra, while RW2 describes operating Luthra Cycle Stores from the disputed premises. The respondent separately mentions his cycle works shop at Shop No. 29/5, Shakti Nagar, Delhi-07; its identity with the disputed shop is not established. The parties' descriptions concern the same disputed shop but do not establish the legal character or commencement of any disposition.",
      "refs": [
        "IK-68065690:L76:span1",
        "IK-68065690:L83:span4",
        "IK-68065690:L84:span5",
        "IK-68065690:L174:context-v4",
        "IK-68065690:L176:context-v4",
        "IK-68065690:L181:context-v4"
      ]
    }
  ],
  "conditions": [
    {
      "arrangement": 1,
      "condition": "DRC_SUBLETTING_C01",
      "assessment": "UNRESOLVED",
      "evidence": [
        {
          "record": 1,
          "role": "UNRESOLVED",
          "connection": "The petitioner alleges subletting but provides no commencement date in the supplied passage."
        },
        {
          "record": 5,
          "role": "CONTEXT",
          "connection": "The reply dated 17 September 2009 documents a later account of possession and family-business involvement, not the date of a disposition."
        },
        {
          "record": 6,
          "role": "UNRESOLVED",
          "connection": "RW1 dates an alleged partnership to 1975 but does not establish that any legally relevant disposition began then."
        }
      ],
      "law_refs": [
        "LAW:S02:DRC14:1b"
      ],
      "explanation": "The alleged partnership's stated inception in 1975 falls after the statutory cutoff, but partnership formation cannot automatically be equated with subletting, assignment or parting with possession. The 2009 reply establishes the date of an account, not the date of the alleged disposition. The temporal requirement therefore remains unresolved.",
      "gaps": [
        "No established date for the alleged transfer of tenancy interest or possession.",
        "The connection between the claimed 1975 partnership and the alleged disposition is unproved."
      ]
    },
    {
      "arrangement": 1,
      "condition": "DRC_SUBLETTING_C02",
      "assessment": "UNRESOLVED",
      "evidence": [
        {
          "record": 1,
          "role": "SUPPORT",
          "connection": "The petitioner alleges monthly rent, subletting and exclusive possession, relevant to the asserted tenancy relationship."
        },
        {
          "record": 3,
          "role": "OPPOSE",
          "connection": "The respondent expressly denies the subletting, alleged rent and exclusive possession."
        },
        {
          "record": 4,
          "role": "OPPOSE",
          "connection": "The respondent describes family-business assistance without rent and continued use of the shop as his own godown."
        },
        {
          "record": 5,
          "role": "OPPOSE",
          "connection": "The recorded reply characterizes Kapil Luthra as a family helper and asserts continued family possession."
        },
        {
          "record": 6,
          "role": "UNRESOLVED",
          "connection": "RW1's oral-partnership testimony suggests another possible business relationship but supplies no established tenancy incidents."
        },
        {
          "record": 7,
          "role": "SUPPORT",
          "connection": "Kapil Luthra's testimony establishes his asserted operation of a business from the premises, supporting an occupation inference but not the complete tenancy proposition."
        }
      ],
      "law_refs": [
        "IK-190902:L109",
        "IK-190902:L110"
      ],
      "explanation": "The alleged Rs.5500/- monthly payment and exclusive possession support the subletting theory but are specifically denied. Kapil Luthra's business activity establishes a relevant connection with the premises, while the family-business and oral-partnership accounts provide competing characterizations. Neither business operation nor partnership terminology independently establishes a transfer of an estate interest, payment of rent and possession as against the respondent in the same purported subtenancy.",
      "gaps": [
        "Actual rent payment and the alleged transfer of a tenancy interest are not independently established.",
        "Kapil Luthra's right to possession as against the respondent remains disputed.",
        "The legal terms of the alleged oral partnership or occupancy arrangement are unknown."
      ]
    },
    {
      "arrangement": 1,
      "condition": "DRC_SUBLETTING_C03",
      "assessment": "UNRESOLVED",
      "evidence": [
        {
          "record": 1,
          "role": "UNRESOLVED",
          "connection": "The allegation of exclusive possession could bear on control but does not specify a divestment of all tenancy rights."
        },
        {
          "record": 3,
          "role": "OPPOSE",
          "connection": "The respondent expressly denies ever assigning the disputed shop."
        },
        {
          "record": 4,
          "role": "OPPOSE",
          "connection": "The respondent claims continuing personal use of the shop as a godown."
        },
        {
          "record": 5,
          "role": "OPPOSE",
          "connection": "The reported legal-notice reply asserts that the respondent's family remains in possession as lawful tenant."
        },
        {
          "record": 7,
          "role": "CONTEXT",
          "connection": "Kapil Luthra's business operation does not establish the respondent's surrender of all tenancy rights."
        }
      ],
      "law_refs": [
        "IK-190902:L109",
        "IK-190902:L110"
      ],
      "explanation": "The respondent's denial of assignment and assertions of continuing possession oppose complete divestment, while the petitioner alleges exclusive occupation by Kapil Luthra. Kapil Luthra's operation of a business does not itself demonstrate that the respondent divested himself of all rights as tenant. The competing accounts do not establish or conclusively negate the complete assignment proposition.",
      "gaps": [
        "No established assignment transaction or terms transferring all tenancy rights.",
        "The respondent's continuing legal rights in the disputed premises are not conclusively determined."
      ]
    },
    {
      "arrangement": 1,
      "condition": "DRC_SUBLETTING_C04",
      "assessment": "UNRESOLVED",
      "evidence": [
        {
          "record": 1,
          "role": "SUPPORT",
          "connection": "The petitioner alleges that Kapil Luthra obtained exclusive possession of the shop."
        },
        {
          "record": 3,
          "role": "OPPOSE",
          "connection": "The respondent specifically denies Kapil Luthra's alleged exclusive possession."
        },
        {
          "record": 4,
          "role": "OPPOSE",
          "connection": "The respondent asserts his own godown use and describes Kapil Luthra as a family-business helper."
        },
        {
          "record": 5,
          "role": "OPPOSE",
          "connection": "The recorded reply asserts continued possession by the respondent's family."
        },
        {
          "record": 6,
          "role": "UNRESOLVED",
          "connection": "The asserted oral partnership may explain shared business activity but does not establish who retained the right to possession."
        },
        {
          "record": 7,
          "role": "SUPPORT",
          "connection": "Kapil Luthra's operation of his stated business from the premises supports his occupation, without independently proving ouster of the respondent."
        }
      ],
      "law_refs": [
        "IK-190902:L107",
        "IK-190902:L111",
        "IK-190902:L112"
      ],
      "explanation": "The petitioner's allegation of exclusive possession and Kapil Luthra's testimony about operating his business provide pertinent evidence of occupation. However, the respondent denies exclusivity and claims continuing family possession and personal godown use. The supplied opinion requires tenant-caused divestment of both physical possession and the right to possession; Kapil Luthra's business operation alone does not resolve that requirement.",
      "gaps": [
        "No established agreement or conduct conclusively identifying the holder of the right to possession.",
        "Whether the respondent was wholly ousted from the relevant premises remains disputed."
      ]
    },
    {
      "arrangement": 1,
      "condition": "DRC_SUBLETTING_C05",
      "assessment": "UNRESOLVED",
      "evidence": [
        {
          "record": 1,
          "role": "SUPPORT",
          "connection": "The petitioner alleges absence of knowledge, consent or permission, encompassing an allegation of no written consent."
        },
        {
          "record": 2,
          "role": "CONTEXT",
          "connection": "The passage reports the petitioner's knowledge of godown use, not written consent to a legally relevant disposition."
        },
        {
          "record": 5,
          "role": "CONTEXT",
          "connection": "The respondent's recorded reply asserts continued family tenancy but does not establish any written consent."
        }
      ],
      "law_refs": [
        "LAW:S02:DRC14:1b"
      ],
      "explanation": "The petitioner's allegation directly supports absence of consent, but remains a party assertion. The separate statement that the petitioner knew about godown use does not establish written consent to subletting, assignment or parting with possession. No supplied instrument or finding conclusively resolves written consent for the alleged disposition, and no presumption is drawn from that absence.",
      "gaps": [
        "No independently established written-consent status for the alleged disposition.",
        "The alleged disposition itself remains disputed, preventing a settled inquiry into consent for that specific transaction."
      ]
    },
    {
      "arrangement": 1,
      "condition": "DRC_SUBLETTING_C06",
      "assessment": "UNRESOLVED",
      "evidence": [
        {
          "record": 1,
          "role": "OPPOSE",
          "connection": "The petitioner alleges exclusive possession by Kapil Luthra, contrary to retained possession."
        },
        {
          "record": 2,
          "role": "CONTEXT",
          "connection": "The reported godown use identifies an activity but does not establish who retained legal possession."
        },
        {
          "record": 3,
          "role": "SUPPORT",
          "connection": "The respondent denies that Kapil Luthra acquired exclusive possession."
        },
        {
          "record": 4,
          "role": "SUPPORT",
          "connection": "The respondent describes personal godown use and Kapil Luthra's assistance in the family business."
        },
        {
          "record": 5,
          "role": "SUPPORT",
          "connection": "The reported 2009 reply expressly asserts continued family possession as lawful tenant."
        },
        {
          "record": 6,
          "role": "CONTEXT",
          "connection": "The alleged oral partnership is consistent with possible concurrent business activity, but does not determine legal possession."
        },
        {
          "record": 7,
          "role": "OPPOSE",
          "connection": "Kapil Luthra's stated operation of his own business from the premises creates a competing inference of independent occupation, without proving ouster."
        }
      ],
      "law_refs": [
        "IK-190902:L107",
        "IK-190902:L112"
      ],
      "explanation": "The respondent's assertions of continued family possession and Kapil Luthra's assistance support a retained-possession or concurrent-use account. The petitioner's exclusive-possession allegation and Kapil Luthra's testimony about operating Luthra Cycle Stores create material opposition. The supplied evidence does not determine whether the respondent retained legal possession of the same relevant part; this qualification therefore remains unresolved.",
      "gaps": [
        "The parties' respective legal rights to occupy or exclude others are not established.",
        "Whether family assistance, partnership activity and Kapil Luthra's business operation involved concurrent use of the same part is unclear."
      ]
    },
    {
      "arrangement": 1,
      "condition": "DRC_SUBLETTING_C07",
      "assessment": "SUPPORTED",
      "evidence": [
        {
          "record": 1,
          "role": "SUPPORT",
          "connection": "The petitioner expressly locates the alleged subletting and exclusive possession in the disputed shop."
        },
        {
          "record": 3,
          "role": "CONTEXT",
          "connection": "The respondent's denial concerns the same disputed shop, rather than another identified premises."
        },
        {
          "record": 4,
          "role": "CONTEXT",
          "connection": "The respondent identifies continuing godown use of the disputed shop while mentioning a separate cycle works shop."
        },
        {
          "record": 7,
          "role": "SUPPORT",
          "connection": "Kapil Luthra identifies the disputed premises as the place where he operates Luthra Cycle Stores."
        }
      ],
      "law_refs": [
        "LAW:S02:DRC14:1b"
      ],
      "explanation": "The alleged disposition expressly concerns the shop in dispute, and Kapil Luthra confirms conducting business from those premises. The required spatial connection to the whole or a part of the disputed premises is therefore supported. This limited assessment identifies the premises involved and does not independently establish that a legally qualifying disposition occurred.",
      "gaps": [
        "The precise area occupied by each person is not established.",
        "The legal character of the alleged disposition remains disputed."
      ]
    }
  ],
  "limitations": [
    {
      "arrangement": 1,
      "condition": "DRC_SUBLETTING_C01",
      "records": [
        6
      ],
      "effect": "NOTE",
      "reason": "RW1's claimed partnership inception in 1975 cannot independently date the alleged subletting, assignment or parting with possession. The relationship between partnership formation and disposition remains unestablished.",
      "refs": [
        "IK-68065690:L176:context-v4",
        "LAW:S02:DRC14:1b"
      ]
    },
    {
      "arrangement": 1,
      "condition": "DRC_SUBLETTING_C05",
      "records": [
        2
      ],
      "effect": "NOTE",
      "reason": "Knowledge of godown use must not be treated as written consent to the particular statutory disposition. The passage also lacks an independently established speaker.",
      "refs": [
        "IK-68065690:L80:span2",
        "LAW:S02:DRC14:1b"
      ]
    },
    {
      "arrangement": 1,
      "condition": "DRC_SUBLETTING_C02",
      "records": [
        6,
        7
      ],
      "effect": "NOTE",
      "reason": "The oral-partnership account and Kapil Luthra's testimony about his business are relevant to the relationship and use of the premises, but neither independently establishes all required tenancy incidents.",
      "refs": [
        "IK-68065690:L176:context-v4",
        "IK-68065690:L181:context-v4",
        "IK-190902:L110"
      ]
    }
  ],
  "coverage_limits": [
    "The supplied case material consists of selected pre-target accounts of pleadings, a reported reply to a legal notice and witness testimony. It does not establish their final acceptance by the Additional Rent Controller after remand.",
    "The supplied passages do not independently establish the alleged rent payments, a transfer of tenancy rights, written consent, the terms governing legal possession or the date of the alleged disposition. Absence of these materials is not treated as proof of their nonexistence.",
    "The supplied legal sources do not determine burden allocation, standard of proof, evidentiary presumptions or the method for dating a continuing arrangement. No additional legal rules are assumed.",
    "The assessments concern individual propositions for the identified arrangement, distinguish allegations from testimony and recorded accounts, and do not predict the final Section 14(1)(b) findings or the request outcome."
  ]
}
```
