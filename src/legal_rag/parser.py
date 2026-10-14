import re

import pdfplumber

from legal_rag.schemas import ArticleRecord
from legal_rag.text_normalizer import (
    extract_article_number,
    fix_visual_arabic,
    normalize_arabic,
    normalize_english,
)

REPEALED_RANGES = {
    (54, 80): {
        "topic": "Associations and Foundations / الجمعيات والمؤسسات",
        "text_ar": "ألغيت المواد من 54 إلى 80 بالقرار الجمهوري بالقانون رقم 348 لسنة 1956 ثم ألغي بالقرار الجمهوري رقم 32 لسنة 1964.",
        "text_en": "Articles 54 to 80 have been repealed by Presidential Decree Law No. 348 of 1956, subsequently repealed by Presidential Decree No. 32 of 1964.",
        "book": "General Provisions / أحكام عامة",
        "chapter": "Persons / الأشخاص",
        "section": "Juristic Persons / الأشخاص الاعتبارية",
    },
    (389, 417): {
        "topic": "Proof of Obligations / إثبات الالتزام",
        "text_ar": "ألغيت المواد من 389 إلى 417 بموجب قانون الإثبات في المواد المدنية والتجارية رقم 25 لسنة 1968.",
        "text_en": "Articles 389 to 417 have been repealed by Law No. 25 of 1968 (Law of Evidence in Civil and Commercial Matters).",
        "book": "Obligations Generally / الالتزامات بوجه عام",
        "chapter": "Proof of Obligations / إثبات الالتزام",
        "section": "Proof / الإثبات",
    },
}

CANONICAL_FALLBACKS: dict[int, dict[str, str]] = {
    83: {
        "book": "General Provisions / أحكام عامة",
        "chapter": "Sources of Law / مصادر القانون",
        "section": "SECTION III / The Classification of Things and Property",
        "topic": "General Provisions / أحكام عامة",
        "text_ar": "(1) يعتبر مالا عقاريا كل حق عيني يقع على عقار، بما في ذلك حق الملكية، وكذلك كل دعوى تتعلق بحق عيني على عقار. (2) ويعتبر مالا منقولا ما عدا ذلك من الحقوق المالية.",
        "text_en": "(1) All real rights over immovable property including the right of ownership and all suits relating to a real right over an immovable are deemed to be immovable property. (2) All other proprietary rights are deemed to be movable property.",
        "source_page": 7,
    },
    120: {
        "book": "BOOK I / Obligations Generally",
        "chapter": "CHAPTER I / Sources of Obligations",
        "section": "Section I / Contracts",
        "topic": "Vices of Consent / عيوب الرضاء",
        "text_ar": "إذا وقع المتعاقد في غلط جوهري جاز له أن يطلب إبطال العقد، إذا كان المتعاقد الآخر قد وقع مثله في هذا الغلط، أو كان على علم به، أو كان من السهل عليه أن يتبينه.",
        "text_en": "A party to a contract may demand the avoidance of the contract if he committed an essential mistake, if the other party committed the same mistake or had knowledge thereof, or could have easily detected the mistake.",
        "source_page": 12,
    },
    203: {
        "book": "BOOK I / Obligations Generally",
        "chapter": "CHAPTER II / The Effects of Obligations",
        "section": "Section I / Specific Performance",
        "topic": "Specific Performance / التنفيذ العيني",
        "text_ar": "(1) يجبر المدين بعد إعذاره طبقا للمادتين 219 و220 على تنفيذ التزامه عينا، إذا كان ذلك ممكنا. (2) على أنه إذا كان في التنفيذ العيني إرهاق للمدين جاز له أن يقتصر على دفع تعويض نقدي، إذا كان ذلك لا يلحق بالدائن ضررا جسيما.",
        "text_en": "(1) A debtor shall be compelled, upon being summoned to do so in accordance with Articles (219) and (220), specifically to perform his obligation, if such performance is possible. (2) When, however, specific performance is too onerous for the debtor, he may limit performance to payment of a sum of money as indemnity, provided that this method of performance does not seriously prejudice the creditor.",
        "source_page": 24,
    },
    387: {
        "book": "BOOK I / Obligations Generally",
        "chapter": "Chapter V / The Extinction of Obligations",
        "section": "Section III / The Extinction of Obligations without Payment",
        "topic": "Prescription / التقادم",
        "text_ar": "(1) لا يجوز للمحكمة أن تقضي بالتقادم من تلقاء نفسها، بل يجب أن يكون ذلك بناء على طلب المدين أو بناء على طلب دائنيه أو أي شخص له مصلحة فيه ولو لم يتمسك به المدين. (2) ويجوز التمسك بالتقادم في أية حالة كانت عليها الدعوى ولو أمام المحكمة الاستئنافية.",
        "text_en": "(1) The judge at his own initiative cannot invoke prescription. Prescription must be invoked by the debtor, or his creditors, or by any interested party, even if the debtor has failed to do so. (2) Prescription may be invoked at any stage of the proceedings, even before the Court of Appeal.",
        "source_page": 52,
    },
    676: {
        "book": "BOOK II / Specific Contracts",
        "chapter": "Chapter III / Contracts for the Hire of Services",
        "section": "Section II / Contracts of Service",
        "topic": "Contracts of Service / عقد العمل",
        "text_ar": "(1) تسري الأحكام الواردة في هذا الفصل على العلاقات ما بين أرباب الأعمال وبين الطوافين والممثلين التجاريين وجابيي المحال التجارية وغيرهم من الوسطاء، ولو كانوا مأجورين بطريق العمالة أو كانوا يعملون لحساب عدة من أرباب الأعمال في وقت واحد، ما دام هؤلاء الأشخاص يعملون تحت إشراف أرباب الأعمال ورقابتهم. (2) وإذا انتهت خدمات الممثل التجاري أو الطواف، ولو كان ذلك بانتهاء الأجل المعين في عقد الاستخدام، كان له الحق في أن يتقاضى على سبيل الأجر العمالة أو الخصم المتفق عليه أو الذي يقضي به العرف عن التوصيات التي لم تبلغ رب العمل إلا بعد خروج الممثل التجاري أو الطواف من خدمته، متى كانت هذه التوصيات نتيجة مباشرة لما قام به من مساع لدى العملاء أثناء خدمته، على أنه لا يجوز التمسك بهذا الحق إلا خلال المدة المعتادة التي يقررها العرف لكل نوع من أنواع التجارة.",
        "text_en": "(1) The provisions of this Section as to contracts of service apply to the relationship between masters and canvassers, commercial representatives, commercial travellers, assurance agents and other intermediaries, even if they remunerated on a commission basis or if they work for the account of several employers at the same time, so long as these persons work under the orders and supervision of such masters. (2) When the services of a commercial representative or a commercial traveller comes to an end, even by reason of the expiration of the term of employment specified in the contract, he shall not be entitled to receive, by way of remuneration, the commission or discount, agreed upon or established by custom, or orders which do not reach the master until after the commercial representative or the traveller has left his service, if such orders are the direct result of the employee's representations to customers while he was in the master's service. Such employees, however, can only claim this right during the usual period for such claims established by custom in respect of each business.",
        "source_page": 93,
    },
    798: {
        "book": "BOOK II / Specific Contracts",
        "chapter": "Chapter V / Suretyship",
        "section": "Section II / The Effects of Suretyship",
        "topic": "Relationship between Surety and Debtor / العلاقة بين الكفيل والمدين",
        "text_ar": "(1) يجب على الكفيل أن يخطر المدين قبل أن يقوم بوفاء الدين، وإلا سقط حقه في الرجوع على المدين إذا كان هذا قد وفى الدين أو كانت عنده وقت الاستحقاق أسباب تقضي ببطلان الدين أو بانقضائه. (2) فإذا لم يعارض المدين في الوفاء، بقي للكفيل حقه في الرجوع عليه ولو كان المدين قد وفى الدين أو كانت عنده أسباب تقضي ببطلانه أو بانقضائه.",
        "text_en": "(1) A surety must give the debtor notice before paying, on pain of forfeiture of his right of action against the debtor, if the latter has himself paid the debt or has grounds, at the date of maturity, for having the debt declared void or extinguished. (2) If the debtor does not object to the payment, the surety retains his right of action against him, even though the debtor had himself paid the debt or had grounds for having the debt declared void or extinguished.",
        "source_page": 113,
    },
    799: {
        "book": "BOOK II / Specific Contracts",
        "chapter": "Chapter V / Suretyship",
        "section": "Section II / The Effects of Suretyship",
        "topic": "Relationship between Surety and Debtor / العلاقة بين الكفيل والمدين",
        "text_ar": "إذا وفى الكفيل الدين، كان له أن يحل محل الدائن في جميع حقوقه قبل المدين. ولكن إذا لم يوف إلا بعض الدين، فلا يرجع بما وفاه إلا بعد أن يستوفي الدائن كل حقه من المدين.",
        "text_en": "A surety who has paid the debt is subrogated to all the rights of the creditor against the debtor; if however, he pays only part of the debt, the surety can only exercise such rights in respect of that part he has paid after the creditor has recovered from the debtor the whole of the debt due.",
        "source_page": 113,
    },
    800: {
        "book": "BOOK II / Specific Contracts",
        "chapter": "Chapter V / Suretyship",
        "section": "Section II / The Effects of Suretyship",
        "topic": "Relationship between Surety and Debtor / العلاقة بين الكفيل والمدين",
        "text_ar": "(1) للكفيل الذي وفى الدين أن يرجع على المدين سواء كانت الكفالة قد عقدت بعلمه أو بغير علمه. (2) ويرجع بأصل الدين وبالفوائد والمصروفات، على أنه في المصروفات لا يرجع إلا بالذي دفعه من وقت إخباره المدين الأصلي بالإجراءات التي اتخذت ضده. (3) ويكون للكفيل الحق في الفوائد القانونية عن كل ما قام بدفعه ابتداء من يوم الدفع.",
        "text_en": "(1) A surety who has paid the debt has a right of action against the debtor whether the suretyship was entered into with or without the knowledge of the debtor. (2) This right of action includes the right to claim the capital amount of the debt, interest and expenses. The surety, however, only has a right of action in respect of those expenses which he has incurred from the date he has notified the principal debtor of the proceedings taken against him. (3) A surety is entitled to interest at the legal rate on all amounts that he has paid from the date of payment.",
        "source_page": 113,
    },
    801: {
        "book": "BOOK II / Specific Contracts",
        "chapter": "Chapter V / Suretyship",
        "section": "Section II / The Effects of Suretyship",
        "topic": "Relationship between Surety and Debtor / العلاقة بين الكفيل والمدين",
        "text_ar": "إذا تعدد المدينون في دين واحد وكانوا متضامنين، فللكفيل الذي ضمنهم جميعا أن يرجع على أي منهم بجميع ما وفاه من الدين.",
        "text_en": "When there are several debtors jointly liable for one and the same debt, a surety who has guaranteed them all, has a remedy against each of them for all that he has paid in respect of the debt.",
        "source_page": 113,
    },
    802: {
        "book": "BOOK III / The Principal Real Rights",
        "chapter": "Chapter I / The Right of Ownership",
        "section": "Section I / The Right of Ownership in General",
        "topic": "Scope of Ownership / نطاق حق الملكية",
        "text_ar": "لمالك الشيء وحده، في حدود القانون، حق استعماله واستغلاله والتصرف فيه.",
        "text_en": "The owner of a thing has alone, within the limits of the law, the right to use, enjoy and dispose of it.",
        "source_page": 113,
    },
    803: {
        "book": "BOOK III / The Principal Real Rights",
        "chapter": "Chapter I / The Right of Ownership",
        "section": "Section I / The Right of Ownership in General",
        "topic": "Scope of Ownership / نطاق حق الملكية",
        "text_ar": "(1) مالك الشيء يملك كل ما يعد من عناصره الجوهرية بحيث لا يمكن فصله عنه دون أن يهلك أو يتلف أو يتغير. (2) وتملك الأرض يشمل ما فوقها وما تحتها إلى الحد المفيد في التمتع بها، علوا أو عمقا. (3) ويجوز بمقتضى القانون أو الاتفاق أن تكون ملكية سطح الأرض منفصلة عن ملكية ما فوقها أو ما تحتها.",
        "text_en": "(1) The owner of a thing also owns everything that constitutes an essential element of the thing owned and which cannot be separated therefrom without the thing owned perishing, deteriorating or changing. (2) The ownership of land includes that which is above and below, as far as it can be usefully enjoyed in height and depth. (3) The ownership of the surface may be separated from that of what is above or below it, by virtue of the law or of an agreement.",
        "source_page": 113,
    },
    1017: {
        "book": "BOOK III / The Principal Real Rights",
        "chapter": "Chapter II / Rights Derived From the Right of Ownership",
        "section": "Section III / Servitudes",
        "topic": "Servitudes / الارتفاق",
        "text_ar": "(1) يجوز أن يترتب الارتفاق على تخصيص من المالك الأصلي. (2) ويكون هذا التخصيص إذا تبين بأي طريق من طرق الإثبات أن مالك عقارين منفصلين قد أقام بينهما علامة ظاهرة، فأنشأ بذلك علاقة تبعية بينهما من شأنها أن تدل على وجود ارتفاق لو أن العقارين كانا مملوكين لمالكين مختلفين. فإذا انتقل العقاران إلى أيدي ملاك مختلفين دون تغيير في حالتهما، عد الارتفاق مرتبا بين العقارين لهما وعليهما مالم يكن ثمة شرط صريح يخالف ذلك.",
        "text_en": "(1) Apparent servitudes may also be created by the intention of the original owner. (2) An intention of the original owner is deemed to exist when it is established, by any means of proof, that the owner of two separate properties has made between the two properties an apparent distinction, thereby creating a relationship of subordination between them which would indicate the existence of a servitude if the two properties belonged to different owners. If, in such a case, the two properties pass into the hands of different owners without any change in their condition, a servitude is deemed, in the absence of a clear condition to the contrary, to have been constituted to the benefit of or as a burden on the two properties respectively.",
        "source_page": 147,
    },
    1018: {
        "book": "BOOK III / The Principal Real Rights",
        "chapter": "Chapter II / Rights Derived From the Right of Ownership",
        "section": "Section III / Servitudes",
        "topic": "Servitudes / الارتفاق",
        "text_ar": "(1) إذا فرضت قيود معينة تحد من حق صاحب العقار في البناء عليه كالحرمان من تجاوز حد معين في الارتفاع أو في مساحة رقعة البناء، فإن هذه القيود تكون ارتفاقات متبادلة لفائدة العقارات التي فرضت لمصلحتها هذه القيود، هذا ما لم يكن هناك اتفاق يقضي بغيره. (2) وكل مخالفة لهذه القيود تجيز المطالبة بإصلاحها عينا، ومع ذلك يجوز للمحكمة أن تقتصر على الحكم بالتعويض إذا رأت أن هناك ما يبرر ذلك.",
        "text_en": "(1) In the absence of an agreement to the contrary, if specific restrictions have been imposed limiting the right of the owner of a property to build freely thereon, such as the prohibition to build above a certain height or on an area in excess of a specific area, such restrictions constitute servitudes which are burdens on the property concerned in favor of properties to whose benefit these restrictions have been imposed. (2) Any breach of these servitudes gives rise to a claim for material redress. The court may, however, only grant damages if it considers that there are reasons for so doing.",
        "source_page": 147,
    },
    1019: {
        "book": "BOOK III / The Principal Real Rights",
        "chapter": "Chapter II / Rights Derived From the Right of Ownership",
        "section": "Section III / Servitudes",
        "topic": "Servitudes / الارتفاق",
        "text_ar": "تخضع الارتفاقات للقواعد المقررة في سند إنشائها ولما يقضي به عرف الجهة وللأحكام الآتية.",
        "text_en": "Servitudes are governed by rules laid down in the deed by which they are created, by local custom and by the following provisions.",
        "source_page": 147,
    },
    1020: {
        "book": "BOOK III / The Principal Real Rights",
        "chapter": "Chapter II / Rights Derived From the Right of Ownership",
        "section": "Section III / Servitudes",
        "topic": "Servitudes / الارتفاق",
        "text_ar": "(1) لمالك العقار المرتفق أن يجري من الأعمال ما هو ضروري لاستعمال حقه في الارتفاق، وما يلزم للمحافظة عليه، وأن يستعمل هذا الحق على الوجه الذي لا ينشأ عنه إلا أقل ضرر ممكن. (2) ولا يجوز أن يترتب على ما يجد من حاجات العقار المرتفق أية زيادة في عبء الارتفاق.",
        "text_en": "(1) The owner of the dominant tenement is entitled to carry out any works necessary to use and preserve his right of servitude; he must use his right in the least harmful manner possible. (2) No requirements of the dominant tenement can entail any increase in the burden of the servitude.",
        "source_page": 147,
    },
    1021: {
        "book": "BOOK III / The Principal Real Rights",
        "chapter": "Chapter II / Rights Derived From the Right of Ownership",
        "section": "Section III / Servitudes",
        "topic": "Servitudes / الارتفاق",
        "text_ar": "لا يلزم مالك العقار المرتفق به أن يقوم بأي عمل لمصلحة العقار المرتفق إلا أن يكون عملا إضافيا يقتضيه استعمال الارتفاق على الوجه المألوف، ما لم يشترط غير ذلك.",
        "text_en": "In the absence of an agreement to the contrary, the owner of the servient tenement is under no obligation to carry out work for the benefit of the dominant tenement, unless it is an accessory work necessitated by the normal use of the servitude.",
        "source_page": 147,
    },
    1022: {
        "book": "BOOK III / The Principal Real Rights",
        "chapter": "Chapter II / Rights Derived From the Right of Ownership",
        "section": "Section III / Servitudes",
        "topic": "Servitudes / الارتفاق",
        "text_ar": "(1) نفقة الأعمال اللازمة لاستعمال حق الارتفاق والمحافظة عليه تكون على مالك العقار المرتفق، مالم يشترط غير ذلك. (2) فإذا كان مالك العقار المرتفق به هو المكلف بالقيام بهذه الأعمال على نفقته، كان له دائما أن يتخلص من هذا التكليف بالتخلي عن العقار المرتفق به كله أو بعضه لمالك العقار المرتفق. (3) وإذا كانت الأعمال نافعة أيضا لمالك العقار المرتفق به، كانت نفقة الصيانة على الطرفين كل بنسبة ما يعود عليه من الفائدة.",
        "text_en": "(1) In the absence of an agreement to the contrary, the cost of the necessary works for the use and preservation of the servitude must be borne by the owner of the dominant tenement. (2) If the owner of the servient tenement is responsible for carrying out these works at his own cost, he has always the right to free himself of this burden by abandoning the servient tenement wholly or in part to the owner of the dominant property. (3) If the works also benefit the owner of the servient tenement, the cost of upkeep falls on the two parties in proportion to the profit derived by each of them.",
        "source_page": 147,
    },
    1023: {
        "book": "BOOK III / The Principal Real Rights",
        "chapter": "Chapter II / Rights Derived From the Right of Ownership",
        "section": "Section III / Servitudes",
        "topic": "Servitudes / الارتفاق",
        "text_ar": "(1) لا يجوز لمالك العقار المرتفق به أن يعمل شيئا يؤدي إلى الانتقاص من استعمال حق الارتفاق أو جعله أكثر مشقة. ولا يجوز له بوجه خاص أن يغير من الوضع القائم أو أن يبدل بالموضع المعين أصلا لاستعمال حق الارتفاق موضعا آخر. (2) ومع ذلك إذا كان الموضع الذي عين أصلا قد أصبح من شأنه أن يزيد في عبء الارتفاق، أو أصبح الارتفاق مانعا من إحداث تحسينات في العقار المرتفق به، كان لمالك هذا العقار أن يطلب نقل الارتفاق إلى موضع آخر من العقار، أو إلى عقار آخر يملكه هو أو يملكه أجنبي إذا رضي الأجنبي بذلك، كل هذا متى كان استعمال الارتفاق في وضعه الجديد ميسورا لمالك العقار المرتفق بالقدر الذي كان ميسورا به في وضعه السابق.",
        "text_en": "(1) The owner of the servient tenement has no right to do anything which will tend to diminish the use made of the servitude or to make it more inconvenient. He cannot, in particular, either change the condition in which the land was or change the place originally fixed for the use of the servitude by another. (2) When, however, the place originally fixed has become such as to increase the burden of the servitude or to prevent the owner of the servient tenement making useful improvements to his property, he may demand that the servitude be transferred to another part of the property, or to another property belonging to him or to a third party who consents thereto, provided that the owner of the dominant tenement can exercise his rights of servitude as easily as he was able to do before the change.",
        "source_page": 147,
    },
    1024: {
        "book": "BOOK III / The Principal Real Rights",
        "chapter": "Chapter II / Rights Derived From the Right of Ownership",
        "section": "Section III / Servitudes",
        "topic": "Servitudes / الارتفاق",
        "text_ar": "(1) إذا جزئ العقار المرتفق بقي الارتفاق مستحقا لكل جزء منه، على ألا يزيد ذلك في العبء الواقع على العقار المرتفق به. (2) غير أنه إذا كان حق الارتفاق لا يفيد في الواقع إلا بعض هذه الأجزاء، كان لمالك العقار المرتفق به أن يطلب إسقاط هذا الحق عن الأجزاء الأخرى.",
        "text_en": "(1) If the dominant tenement is divided, the servitude continues to benefit each part thereof, provided that the burden on the servient property is not increased. (2) If, however, the servitude only benefits one of the divided parts of the dominant tenement, the owner of the servient tenement may demand that it ceases as regards the other parts.",
        "source_page": 148,
    },
    1025: {
        "book": "BOOK III / The Principal Real Rights",
        "chapter": "Chapter II / Rights Derived From the Right of Ownership",
        "section": "Section III / Servitudes",
        "topic": "Servitudes / الارتفاق",
        "text_ar": "(1) إذا جزئ العقار المرتفق به بقي حق الارتفاق واقعا على كل جزء منه. (2) غير أنه إذا كان حق الارتفاق لا يستعمل في الواقع على بعض هذه الأجزاء ولا يمكن أن يستعمل عليها، كان لمالك كل جزء منها أن يطلب إسقاط هذا الحق عن الجزء الذي يخصه.",
        "text_en": "(1) If the servient tenement is divided, the servitude continues to subsist in respect of each part thereof. (2) If, however, the servitude is not actually used and cannot be used on certain of these divided parts, the owner of each of them may demand that it ceases as regards the part belonging to him.",
        "source_page": 148,
    },
    1026: {
        "book": "BOOK III / The Principal Real Rights",
        "chapter": "Chapter II / Rights Derived From the Right of Ownership",
        "section": "Section III / Servitudes",
        "topic": "Servitudes / الارتفاق",
        "text_ar": "تنتهي حقوق الارتفاق بانقضاء الأجل المعين، وبهلاك العقار المرتفق به أو العقار المرتفق هلاكا تاما، وباجتماع العقارين في يد مالك واحد، إلا أنه إذا زالت حالة الاجتماع هذه زوالا يرجع أثره إلى الماضي فإن حق الارتفاق يعود.",
        "text_en": "Servitudes are extinguished by the expiration of the period for which they were created, by the total destruction of the servient or dominant tenement or by the merger of the two tenements in the hands of one owner. The servitude is, however, revived if the merger of the two tenements ceases with retroactive effect.",
        "source_page": 148,
    },
    1027: {
        "book": "BOOK III / The Principal Real Rights",
        "chapter": "Chapter II / Rights Derived From the Right of Ownership",
        "section": "Section III / Servitudes",
        "topic": "Servitudes / الارتفاق",
        "text_ar": "(1) ينتهي حق الارتفاق بعدم استعماله مدة خمس عشرة سنة، فإذا كان الارتفاق مقررا لمصلحة عين موقوفة كانت المدة ثلاثا وثلاثين سنة. وكما يسقط الارتفاق بعدم الاستعمال يجوز كذلك أن يعدل من كيفيته بعدم استعماله بالقدر ذاته في المدة ذاتها. (2) وإذا ملك العقار المرتفق عدة شركاء على الشيوع، فانتفاع أحدهم بالارتفاق يقطع التقادم لمصلحة الباقين، كما أن وقف التقادم لمصلحة أحد الشركاء يجعله موقوفا لمصلحة سائرهم.",
        "text_en": "(1) Servitudes are extinguished by non-user for a period of fifteen years; if the servitude is constituted for the benefit of a wakf property, the period will be thirty-three years. In the same way that a servitude is extinguished by non-user, it may also be modified by partial non-user during the same period. (2) If the dominant tenement belongs to several co-owners in common, the use of the servitude by one of them interrupts the prescription as regards the other co-owners; similarly, the suspension of prescription in favor of one of the co-owners suspends it in favor of the others.",
        "source_page": 148,
    },
    1110: {
        "book": "BOOK IV / Accessory Rights or Real Securities",
        "chapter": "Chapter III / Rights Derived from the Right of Ownership Pledge",
        "section": "Section II / The Effects of a Pledge",
        "topic": "The Effects of a Pledge / آثار الرهن الحيازي",
        "text_ar": "(1) يخول الرهن الدائن المرتهن الحق في حبس الشيء المرهون عن الناس كافة، دون إخلال بما للغير من حقوق تم حفظها وفقا للقانون. (2) وإذا خرج الشيء من يد الدائن دون إرادته أو دون علمه، كان له الحق في استرداد حيازته من الغير وفقا لأحكام الحيازة.",
        "text_en": "(1) Pledge confers upon the pledgee the right to retain the thing pledged against all persons, without prejudice to the rights of third parties which have been preserved in accordance with the law. (2) If a pledgee loses possession of the thing without his knowledge or against his will, he has the right to recover possession from any other person in accordance with the provisions of the law as to possession.",
        "source_page": 162,
    },
    1115: {
        "book": "BOOK IV / Accessory Rights or Real Securities",
        "chapter": "Chapter III / Rights Derived from the Right of Ownership Pledge",
        "section": "Section IV / Certain Kinds of Pledge",
        "topic": "Pledge of an Immovable / الرهن العقاري",
        "text_ar": "يجوز للدائن المرتهن لعقار أن يؤجر العقار إلى الراهن دون أن يمنع ذلك من نفاذ الرهن في حق الغير. فإذا اتفق على الإيجار في عقد الرهن وجب ذكر ذلك في القيد ذاته. أما إذا اتفق عليه بعد الرهن وجب أن يؤشر به في هامش القيد، إلا أن هذا التأشير لا يكون ضروريا إذا جدد الإيجار تجديدا ضمنيا.",
        "text_en": "A pledgee of an immovable may lease the immovable to the pledgor without the contract of pledge being less valid as against third parties. If the lease is agreed to in the contract of pledge, it must be mentioned in the inscription of the pledge, but if the lease is agreed to after the pledge, it must be noted in the margin of that inscription. Notation is not necessary if the lease is tacitly renewed.",
        "source_page": 163,
    },
}


class CivilCodeParser:
    def __init__(self, pdf_path: str):
        self.pdf_path = pdf_path
        self.current_book = "General Provisions / أحكام عامة"
        self.current_chapter = "Sources of Law / مصادر القانون"
        self.current_section = "General / عام"
        self.current_topic = "General Provisions / أحكام عامة"
        self.last_article_num = None

    def _is_hierarchy_heading(self, text_ar: str, text_en: str) -> bool:
        norm_ar = text_ar.strip()
        norm_en = text_en.strip()

        if "الكتاب" in norm_ar or re.search(r"^\s*BOOK\b", norm_en, re.IGNORECASE):
            self.current_book = norm_en or norm_ar
            return True
        elif "الباب" in norm_ar or re.search(r"^\s*CHAPTER\b", norm_en, re.IGNORECASE):
            self.current_chapter = norm_en or norm_ar
            return True
        elif "الفصل" in norm_ar or re.search(
            r"^\s*SECTION\s+[IVXLCDM0-9]+", norm_en, re.IGNORECASE
        ):
            self.current_section = norm_en or norm_ar
            return True
        elif any(
            norm_ar.startswith(k) for k in ["أولا", "ثانيا", "ثالثا", "رابعا", "خامسا", "١-", "٢-"]
        ):
            self.current_topic = norm_en or norm_ar
            return True
        return False

    def _inject_repealed_range(
        self, articles: dict[int, ArticleRecord], start: int, end: int, page_num: int
    ):
        meta = REPEALED_RANGES.get((start, end))
        if not meta:
            return
        for num in range(start, end + 1):
            articles[num] = ArticleRecord(
                article_number=num,
                book=meta["book"],
                chapter=meta["chapter"],
                section=meta["section"],
                topic=meta["topic"],
                text_ar=meta["text_ar"],
                text_en=meta["text_en"],
                is_repealed=True,
                source_page=page_num,
                citation=f"Egyptian Civil Code, Article {num} (Repealed)",
            )

    def parse(self) -> list[ArticleRecord]:
        raw_articles: dict[int, dict] = {}

        with pdfplumber.open(self.pdf_path) as pdf:
            for page_idx, page in enumerate(pdf.pages):
                page_num = page_idx + 1
                tables = page.extract_tables()
                if tables:
                    for table in tables:
                        for row in table:
                            if not row or len(row) < 2:
                                continue
                            col_en = row[0] or ""
                            col_ar = row[1] or ""
                            self._process_row(col_ar, col_en, page_num, raw_articles)

        articles: dict[int, ArticleRecord] = {}

        # 1. Process all collected raw articles
        for num, item in raw_articles.items():
            text_ar = item["text_ar"].strip()
            text_en = item["text_en"].strip()

            # If text is too short, check canonical fallbacks
            if len(text_ar) < 5 or len(text_en) < 5:
                if num in CANONICAL_FALLBACKS:
                    fb = CANONICAL_FALLBACKS[num]
                    text_ar = normalize_arabic(fb["text_ar"])
                    text_en = normalize_english(fb["text_en"])
                    item["book"] = fb.get("book", item["book"])
                    item["chapter"] = fb.get("chapter", item["chapter"])
                    item["section"] = fb.get("section", item["section"])
                    item["topic"] = fb.get("topic", item["topic"])
                else:
                    if len(text_ar) >= 5 and len(text_en) < 5:
                        text_en = text_ar
                    elif len(text_en) >= 5 and len(text_ar) < 5:
                        text_ar = text_en

            if len(text_ar) >= 5 and len(text_en) >= 5:
                articles[num] = ArticleRecord(
                    article_number=num,
                    book=item["book"],
                    chapter=item["chapter"],
                    section=item["section"],
                    topic=item["topic"],
                    text_ar=text_ar,
                    text_en=text_en,
                    is_repealed=False,
                    source_page=item["source_page"],
                    citation=f"Egyptian Civil Code, Article {num}",
                )

        # 2. Inject canonical fallbacks for borderless pages / missing articles
        for num, fb in CANONICAL_FALLBACKS.items():
            if num not in articles or len(articles[num].text_ar.strip()) < 5:
                articles[num] = ArticleRecord(
                    article_number=num,
                    book=fb["book"],
                    chapter=fb["chapter"],
                    section=fb["section"],
                    topic=fb["topic"],
                    text_ar=normalize_arabic(fb["text_ar"]),
                    text_en=normalize_english(fb["text_en"]),
                    is_repealed=False,
                    source_page=fb["source_page"],
                    citation=f"Egyptian Civil Code, Article {num}",
                )

        # 3. Inject repealed ranges
        self._inject_repealed_range(articles, 54, 80, 7)
        self._inject_repealed_range(articles, 389, 417, 53)

        return sorted(articles.values(), key=lambda x: x.article_number)

    def _process_row(self, col_ar: str, col_en: str, page_num: int, raw_articles: dict[int, dict]):
        fixed_ar = fix_visual_arabic(col_ar)

        art_num = (
            extract_article_number(fixed_ar)
            or extract_article_number(col_ar)
            or extract_article_number(col_en)
        )

        # Never process repealed ranges from raw rows
        if art_num and (54 <= art_num <= 80 or 389 <= art_num <= 417):
            return

        if art_num:
            clean_ar = re.sub(
                r"^\s*(?:مادة\s*[\(\[]?\s*[0-9٠-٩]+\s*[\)\]]?|[\(\[]?\s*[0-9٠-٩]+\s*[\)\]]?\s*مادة|[0-9٠-٩]+\s*ةدام|ةدام\s*[0-9٠-٩]+|\([0-9٠-٩]+\s*\(\s*ةدام)\s*[:\-\.]?\s*",
                "",
                fixed_ar,
                flags=re.DOTALL,
            )
            clean_en = re.sub(
                r"^\s*A?rticle\s*[0-9]+\s*[:\-\.]?\s*",
                "",
                col_en,
                flags=re.DOTALL | re.IGNORECASE,
            )

            clean_ar = normalize_arabic(clean_ar)
            clean_en = normalize_english(clean_en)

            if art_num not in raw_articles:
                raw_articles[art_num] = {
                    "article_number": art_num,
                    "book": self.current_book,
                    "chapter": self.current_chapter,
                    "section": self.current_section,
                    "topic": self.current_topic,
                    "text_ar": clean_ar,
                    "text_en": clean_en,
                    "source_page": page_num,
                }
            else:
                if clean_ar:
                    raw_articles[art_num][
                        "text_ar"
                    ] = f"{raw_articles[art_num]['text_ar']}\n{clean_ar}".strip()
                if clean_en:
                    raw_articles[art_num][
                        "text_en"
                    ] = f"{raw_articles[art_num]['text_en']}\n{clean_en}".strip()

            self.last_article_num = art_num
        else:
            is_heading = self._is_hierarchy_heading(fixed_ar, col_en)
            if not is_heading and self.last_article_num and self.last_article_num in raw_articles:
                clean_ar = normalize_arabic(fixed_ar)
                clean_en = normalize_english(col_en)
                prev = raw_articles[self.last_article_num]
                if clean_ar:
                    prev["text_ar"] = (
                        f"{prev['text_ar']}\n{clean_ar}".strip() if prev["text_ar"] else clean_ar
                    )
                if clean_en:
                    prev["text_en"] = (
                        f"{prev['text_en']}\n{clean_en}".strip() if prev["text_en"] else clean_en
                    )
