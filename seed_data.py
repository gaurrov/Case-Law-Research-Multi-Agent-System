"""Seed the cases_corpus table with 18 synthetic legal cases and build embeddings."""
import sys
from db.database import engine, SessionLocal
from db.models import Base, CaseCorpus, CaseEmbedding

SEED_CASES = [
    {
        "case_name": "Henderson v. Pacific Digital Corp.",
        "citation": "145 F.3d 1032 (9th Cir. 2019)",
        "court": "United States Court of Appeals, Ninth Circuit",
        "date": "2019-06-15",
        "summary": "Employee's use of employer-provided laptop for personal activities did not waive employer's right to monitor under company policy.",
        "full_text": """HENDERSON v. PACIFIC DIGITAL CORP.
145 F.3d 1032 (9th Cir. 2019)

OPINION: The central question before this Court is whether an employer's monitoring of employee activity on company-owned devices constitutes an invasion of privacy when the employee has signed an acceptable use policy.

Plaintiff James Henderson was employed as a software engineer at Pacific Digital Corp. from 2015 to 2018. Upon hiring, Henderson signed the company's Technology Acceptable Use Policy, which stated: "All company-owned devices are subject to monitoring. Employees should have no expectation of privacy when using company equipment."

In January 2018, Pacific Digital's IT department flagged Henderson's laptop for excessive bandwidth usage. Upon investigation, they discovered Henderson had been using the laptop for extensive personal activities, including accessing personal email, social media, and cloud storage. Henderson was subsequently terminated.

Henderson filed suit alleging violation of the Electronic Communications Privacy Act and state privacy laws. The district court granted summary judgment in favor of Pacific Digital Corp.

HELD: We affirm. The signed acceptable use policy constituted valid consent to monitoring. An employee who signs a clear, unambiguous monitoring policy cannot later claim a reasonable expectation of privacy on company devices. The monitoring was proportionate to legitimate business interests in network security and productivity.

We note, however, that employers must ensure monitoring policies are clearly communicated and that monitoring does not extend beyond the scope of the stated policy. Covert surveillance beyond the policy's terms would not receive the same deference."""
    },
    {
        "case_name": "Martinez v. City of Riverside",
        "citation": "312 Cal.App.4th 567 (2020)",
        "court": "California Court of Appeal, Fourth District",
        "date": "2020-03-22",
        "summary": "City liable for negligent maintenance of public sidewalk that caused pedestrian injury; governmental immunity did not apply.",
        "full_text": """MARTINEZ v. CITY OF RIVERSIDE
312 Cal.App.4th 567 (2020)

OPINION: This appeal concerns municipal liability for dangerous conditions on public property under California Government Code section 835.

Plaintiff Rosa Martinez suffered severe injuries when she tripped over a raised section of sidewalk on Main Street in Riverside. The raised section, caused by tree root growth, had been the subject of three prior citizen complaints over a two-year period, none of which resulted in repairs.

The City argued governmental immunity under Government Code section 815, asserting that the decision not to repair was a discretionary act. The trial court disagreed, finding that once the City had actual notice of the dangerous condition, the failure to repair or warn was operational negligence, not a protected policy decision.

HELD: Affirmed. Under Government Code section 835, a public entity is liable for injury caused by a dangerous condition of public property if the entity had actual or constructive notice of the condition and failed to take adequate protective measures. The three prior complaints established actual notice. The City's failure to repair or even place warning markers constituted negligence.

The distinction between discretionary policy decisions (immune) and operational negligence (not immune) is well established. Allocating resources among competing priorities is discretionary; ignoring repeated specific warnings about a known hazard is operational failure."""
    },
    {
        "case_name": "TechVault Inc. v. DataStream Solutions",
        "citation": "891 F.Supp.3d 445 (S.D.N.Y. 2021)",
        "court": "United States District Court, Southern District of New York",
        "date": "2021-01-10",
        "summary": "Trade secret misappropriation found where former employee used proprietary algorithms at new employer; injunctive relief granted.",
        "full_text": """TECHVAULT INC. v. DATASTREAM SOLUTIONS
891 F.Supp.3d 445 (S.D.N.Y. 2021)

OPINION: Plaintiff TechVault Inc. moves for a preliminary injunction against DataStream Solutions and former TechVault employee Dr. Sarah Chen, alleging misappropriation of trade secrets under the Defend Trade Secrets Act (DTSA), 18 U.S.C. § 1836.

Dr. Chen was a lead researcher at TechVault, where she developed proprietary data compression algorithms. Her employment agreement included non-disclosure provisions and an assignment of inventions clause. In September 2020, Dr. Chen resigned and joined DataStream, a direct competitor.

Within three months of Dr. Chen's arrival, DataStream released a product featuring compression technology substantially similar to TechVault's proprietary algorithms. TechVault's expert witness demonstrated that the similarity was "beyond what independent development could explain."

Dr. Chen and DataStream contend that the algorithms were developed independently and represent common knowledge in the field. However, internal communications revealed that DataStream's development timeline was compressed from an estimated 18 months to 3 months after Dr. Chen's hiring.

HELD: Preliminary injunction GRANTED. TechVault has demonstrated a likelihood of success on the merits. The algorithms qualify as trade secrets: they derive independent economic value from not being generally known, and TechVault took reasonable measures to protect them. The circumstantial evidence — the compressed timeline, the technical similarity, and Dr. Chen's access — supports an inference of misappropriation. DataStream is enjoined from selling or marketing the accused product pending trial."""
    },
    {
        "case_name": "In re Greenfield Estates HOA",
        "citation": "78 B.R. 234 (Bankr. D. Ariz. 2020)",
        "court": "United States Bankruptcy Court, District of Arizona",
        "date": "2020-08-05",
        "summary": "Homeowners association's special assessment survived bankruptcy filing; held to be in the nature of a covenant running with the land.",
        "full_text": """IN RE GREENFIELD ESTATES HOA
78 B.R. 234 (Bankr. D. Ariz. 2020)

OPINION: The debtor, owner of a residential unit in Greenfield Estates, seeks to discharge a $15,000 special assessment levied by the homeowners association for community pool repairs.

The HOA's CC&Rs (Covenants, Conditions, and Restrictions) grant the board authority to levy special assessments for common area maintenance and repair. The assessment was approved by a two-thirds vote of the membership in accordance with the CC&Rs.

The debtor argues the special assessment is a dischargeable debt. The HOA contends it is an obligation that runs with the land and survives bankruptcy under 11 U.S.C. § 523(a)(16).

HELD: The special assessment obligation survives the debtor's bankruptcy discharge. Under section 523(a)(16), debts for fees or assessments that become due after the filing of the petition with respect to the debtor's interest in a unit in a condominium or housing cooperative are nondischargeable. Moreover, the assessment is in the nature of a covenant running with the land, binding subsequent owners. The debtor retains the property and must satisfy the assessment to maintain clear title.

This Court recognizes the hardship on the debtor but notes that HOA assessments serve the collective interest of all unit owners. Allowing discharge would shift the financial burden to other homeowners who are equally bound by the CC&Rs."""
    },
    {
        "case_name": "Commonwealth v. Brooks",
        "citation": "482 Mass. 701 (2019)",
        "court": "Supreme Judicial Court of Massachusetts",
        "date": "2019-11-18",
        "summary": "Warrantless search of defendant's cell phone incident to arrest violated Fourth Amendment; evidence suppressed.",
        "full_text": """COMMONWEALTH v. BROOKS
482 Mass. 701 (2019)

OPINION: The defendant, Marcus Brooks, appeals his conviction for drug distribution, arguing that evidence obtained from a warrantless search of his cell phone should have been suppressed.

On March 15, 2018, Officer Davis arrested Brooks on an outstanding warrant. During a search incident to arrest, Officer Davis powered on Brooks' cell phone (which was not password-protected), opened the text messaging application, and read several messages that appeared to describe drug transactions. These messages were admitted at trial over defense objection.

The Commonwealth argues the search was permissible as a search incident to arrest under the automobile exception or under exigent circumstances to prevent destruction of evidence.

HELD: Reversed and remanded. Following the United States Supreme Court's decision in Riley v. California, 573 U.S. 373 (2014), the warrantless search of a cell phone is not justified by the search-incident-to-arrest exception. Cell phones contain vast quantities of personal information that implicate significant privacy interests far beyond those at stake in a search of physical items on a person.

The Commonwealth's destruction-of-evidence argument fails because there was no showing that remote wiping was imminent or likely. The proper course was to secure the phone and obtain a warrant. The evidence obtained from the cell phone search is suppressed, and the case is remanded for a new trial without that evidence."""
    },
    {
        "case_name": "Willow Creek Tribal Council v. State of Oregon",
        "citation": "923 F.3d 1178 (9th Cir. 2020)",
        "court": "United States Court of Appeals, Ninth Circuit",
        "date": "2020-05-30",
        "summary": "State environmental regulation that impacted tribal fishing rights required federal consultation under trust responsibility doctrine.",
        "full_text": """WILLOW CREEK TRIBAL COUNCIL v. STATE OF OREGON
923 F.3d 1178 (9th Cir. 2020)

OPINION: The Willow Creek Tribal Council challenges Oregon's implementation of new water quality regulations that effectively restrict salmon fishing in traditional tribal waters.

The Tribe holds treaty-guaranteed fishing rights under the Treaty of 1855, which reserves "the right of taking fish at all usual and accustomed grounds and stations." Oregon's new regulations, adopted to address endangered species concerns, impose seasonal closures that overlap with the Tribe's traditional fishing season.

Oregon argues that its regulations are a valid exercise of state police power to protect endangered species and that treaty rights must yield to conservation necessity under the Puyallup trilogy.

HELD: The State's regulations, while motivated by legitimate conservation concerns, were adopted without the required federal-tribal consultation process. Treaty fishing rights are not merely permissions granted by the government; they are reservations of pre-existing rights. Any limitation must satisfy the conservation necessity standard: the regulation must be reasonable, necessary for conservation, and must not discriminate against treaty fishers.

We remand for the State to engage in meaningful government-to-government consultation with the Tribe and to develop regulations that accommodate treaty rights while addressing conservation goals. The State must demonstrate that less restrictive alternatives were considered and found inadequate before imposing restrictions on treaty-protected fishing."""
    },
    {
        "case_name": "Patel v. University Hospital System",
        "citation": "567 F.Supp.3d 890 (N.D. Ill. 2021)",
        "court": "United States District Court, Northern District of Illinois",
        "date": "2021-04-14",
        "summary": "Hospital's AI-assisted diagnostic tool did not create independent duty of care; physician retained ultimate diagnostic responsibility.",
        "full_text": """PATEL v. UNIVERSITY HOSPITAL SYSTEM
567 F.Supp.3d 890 (N.D. Ill. 2021)

OPINION: This medical malpractice case raises a novel question: when a hospital deploys an artificial intelligence diagnostic assistance tool, does the AI system's output create an independent standard of care?

Plaintiff Anita Patel presented to the emergency department with chest pain. The attending physician, Dr. Reynolds, used the hospital's AI diagnostic tool, which flagged a potential cardiac event with 78% confidence. Dr. Reynolds, based on his clinical judgment and additional testing, diagnosed musculoskeletal pain and discharged Patel. She suffered a myocardial infarction 12 hours later.

Patel argues that the hospital breached its duty of care by allowing Dr. Reynolds to override the AI tool's recommendation without additional testing.

HELD: Summary judgment DENIED. The AI diagnostic tool does not create an independent duty of care separate from the physician's obligation to exercise reasonable medical judgment. The standard of care remains what a reasonably competent physician would do under the circumstances. However, where a physician has access to an AI tool that flags a significant risk, the decision to override that recommendation must be supported by documented clinical reasoning.

We decline to hold that AI recommendations are dispositive, but we also reject the notion that they can be disregarded without explanation. The standard of care is evolving to incorporate technological tools, and physicians must demonstrate they exercised informed judgment when departing from AI-assisted recommendations."""
    },
    {
        "case_name": "Rogers v. Apex Property Management",
        "citation": "234 F.Supp.3d 112 (D. Md. 2020)",
        "court": "United States District Court, District of Maryland",
        "date": "2020-09-03",
        "summary": "Landlord's algorithmic tenant screening tool had disparate impact on minority applicants; Fair Housing Act violation found.",
        "full_text": """ROGERS v. APEX PROPERTY MANAGEMENT
234 F.Supp.3d 112 (D. Md. 2020)

OPINION: Plaintiffs, a class of rejected rental applicants, allege that Apex Property Management's use of an automated tenant screening algorithm violates the Fair Housing Act, 42 U.S.C. § 3604.

Apex uses a third-party screening tool that evaluates applicants based on credit score, criminal background, eviction history, and income verification. Statistical analysis reveals that the tool rejects Black and Hispanic applicants at 2.4 times the rate of white applicants, even when controlling for income.

Apex argues that the screening criteria are facially neutral and serve legitimate business interests in identifying reliable tenants.

HELD: Judgment for plaintiffs. Under the disparate impact framework established in Texas Department of Housing v. Inclusive Communities Project, 576 U.S. 519 (2015), plaintiffs have demonstrated a prima facie case. The 2.4x rejection disparity is statistically significant. While Apex has articulated legitimate business justifications, it has failed to demonstrate that less discriminatory alternatives were unavailable. Specifically, Apex did not consider alternative screening approaches such as individualized assessment, which could achieve the same business objectives with less discriminatory impact.

The use of an algorithm does not insulate a housing provider from Fair Housing Act liability. Landlords bear responsibility for ensuring that their screening methods — whether human or automated — comply with fair housing requirements."""
    },
    {
        "case_name": "State v. Whitfield",
        "citation": "345 Ga.App. 678 (2021)",
        "court": "Georgia Court of Appeals",
        "date": "2021-02-27",
        "summary": "Defendant's Sixth Amendment right to confrontation was violated when forensic lab report was admitted without analyst testimony.",
        "full_text": """STATE v. WHITFIELD
345 Ga.App. 678 (2021)

OPINION: Defendant Terrence Whitfield appeals his conviction for possession of a controlled substance, arguing that the admission of a forensic laboratory report without live testimony from the analyst who performed the testing violated his Sixth Amendment right to confrontation.

At trial, the State introduced a forensic lab report identifying the seized substance as methamphetamine. The analyst who performed the tests, Dr. Kim, had relocated out of state. Instead, the State called Dr. Foster, a supervisor at the lab, who testified about the general procedures used in the lab but did not personally perform or observe the specific tests on the evidence in this case.

HELD: Reversed. Under Crawford v. Washington, 541 U.S. 36 (2004), and Bullcoming v. New Mexico, 564 U.S. 647 (2011), a forensic lab report is testimonial in nature. The Confrontation Clause requires that the defendant have an opportunity to cross-examine the analyst who actually performed the testing. Surrogate testimony from a supervisor who did not conduct or observe the specific analysis is insufficient.

The State's argument that lab reports are business records exempt from the Confrontation Clause is foreclosed by Melendez-Diaz v. Massachusetts, 557 U.S. 305 (2009). The conviction is reversed and the case is remanded for a new trial."""
    },
    {
        "case_name": "Blue Ridge Conservation Trust v. Mountain Energy LLC",
        "citation": "789 S.E.2d 234 (Va. 2020)",
        "court": "Supreme Court of Virginia",
        "date": "2020-12-01",
        "summary": "Conservation easement was enforceable against subsequent purchaser who had constructive notice; pipeline construction enjoined.",
        "full_text": """BLUE RIDGE CONSERVATION TRUST v. MOUNTAIN ENERGY LLC
789 S.E.2d 234 (Va. 2020)

OPINION: Blue Ridge Conservation Trust seeks to enforce a conservation easement against Mountain Energy LLC, which purchased a 500-acre parcel and plans to construct a natural gas pipeline across it.

The conservation easement was granted in 2010 by the prior owner, recorded in the county land records, and donated to the Trust. The easement prohibits industrial development and restricts the property to agricultural and conservation uses. Mountain Energy purchased the parcel in 2019 and argues the easement is unenforceable because it was not disclosed in the purchase agreement and constitutes an unreasonable restraint on alienation.

HELD: The conservation easement is enforceable. A properly recorded conservation easement constitutes constructive notice to all subsequent purchasers. Mountain Energy's failure to discover the easement during its due diligence does not render it unenforceable. Under Virginia's Conservation Easement Act, Va. Code § 10.1-1009, conservation easements are perpetual unless otherwise stated and are not subject to the traditional common law rules against unreasonable restraints on alienation.

Mountain Energy is permanently enjoined from constructing the pipeline on the encumbered property. The public interest in conservation, combined with the Trust's legitimate property interest, outweighs Mountain Energy's commercial expectations, which were formed without adequate title review."""
    },
    {
        "case_name": "Nakamura v. CloudFirst Technologies",
        "citation": "45 Cal.5th 789 (2021)",
        "court": "Supreme Court of California",
        "date": "2021-07-20",
        "summary": "Mandatory arbitration clause in employment agreement was unconscionable where it waived class action rights and imposed asymmetric discovery limits.",
        "full_text": """NAKAMURA v. CLOUDFIRST TECHNOLOGIES
45 Cal.5th 789 (2021)

OPINION: Plaintiff Kenji Nakamura challenges the enforceability of a mandatory arbitration clause in his employment agreement with CloudFirst Technologies.

The arbitration clause requires all employment disputes to be resolved through binding arbitration, waives the right to participate in class or collective actions, limits discovery to 10 interrogatories and 3 depositions for the employee while imposing no such limits on the employer, and requires the employee to pay half the arbitrator's fees.

Nakamura brought a class action alleging systematic overtime violations affecting approximately 200 software engineers.

HELD: The arbitration clause is unconscionable and unenforceable. Both procedural and substantive unconscionability are present. Procedurally, the clause was presented on a take-it-or-leave-it basis as a condition of employment with no opportunity for negotiation. Substantively, the clause is one-sided: asymmetric discovery limits, fee-splitting that could deter low-value claims, and a class action waiver that effectively immunizes the employer from aggregate liability for small-per-person violations.

While the Federal Arbitration Act favors arbitration, it does not preempt state unconscionability doctrine when applied neutrally to all contracts. An arbitration clause that systematically disadvantages one party is not a mere agreement to arbitrate; it is a mechanism to suppress meritorious claims. The clause is severed, and Nakamura may proceed with his class action in court."""
    },
    {
        "case_name": "Dawson v. Metropolitan School District",
        "citation": "678 F.3d 901 (7th Cir. 2019)",
        "court": "United States Court of Appeals, Seventh Circuit",
        "date": "2019-09-10",
        "summary": "School district's social media monitoring of student accounts off-campus violated First Amendment absent a showing of substantial disruption.",
        "full_text": """DAWSON v. METROPOLITAN SCHOOL DISTRICT
678 F.3d 901 (7th Cir. 2019)

OPINION: Plaintiff Emily Dawson, a high school junior, was suspended for three days after the school district's social media monitoring program flagged her off-campus Instagram post criticizing the school's dress code policy.

The Metropolitan School District implemented a social media monitoring program that uses keyword-based scanning of publicly accessible student social media accounts. Dawson's post described the dress code as "oppressive and sexist" and encouraged other students to attend school in violation of the policy as a form of protest.

The school district argues the post threatened substantial disruption under Tinker v. Des Moines Independent Community School District, 393 U.S. 503 (1969).

HELD: Reversed. The school district violated Dawson's First Amendment rights. Under Tinker, schools may regulate student speech that materially and substantially disrupts school operations. However, speech that merely causes discomfort or expresses disagreement with school policy is protected. Dawson's post was political expression on a matter of school policy — precisely the type of speech Tinker protects.

Moreover, the off-campus nature of the speech raises additional concerns. Following Mahanoy Area School District v. B.L., 141 S. Ct. 2038 (2021), schools have diminished authority over off-campus speech. The school district's proactive monitoring program chills student expression by creating a surveillance environment that discourages participation in public discourse on school issues."""
    },
    {
        "case_name": "Thornton Industries v. EPA",
        "citation": "912 F.3d 445 (D.C. Cir. 2020)",
        "court": "United States Court of Appeals, D.C. Circuit",
        "date": "2020-07-08",
        "summary": "EPA's revocation of Clean Air Act permit was arbitrary and capricious where agency failed to consider reliance interests of permit holder.",
        "full_text": """THORNTON INDUSTRIES v. EPA
912 F.3d 445 (D.C. Cir. 2020)

OPINION: Thornton Industries challenges the EPA's decision to revoke its Clean Air Act operating permit for a manufacturing facility in West Virginia.

Thornton had held a valid permit for 15 years and invested $40 million in pollution control equipment to comply with permit conditions. The EPA revoked the permit based on a reinterpretation of emissions standards, concluding that Thornton's facility exceeded newly calculated limits.

Thornton does not dispute that its emissions exceed the reinterpreted limits but argues that the EPA failed to consider the company's substantial reliance interests and the economic impact of revocation.

HELD: The EPA's revocation is set aside as arbitrary and capricious under the Administrative Procedure Act, 5 U.S.C. § 706(2)(A). An agency must consider and address significant reliance interests when changing its position. See FCC v. Fox Television Stations, Inc., 556 U.S. 502 (2009); Department of Homeland Security v. Regents of the University of California, 140 S. Ct. 1891 (2020).

The EPA's failure to consider Thornton's $40 million investment, the 15-year history of compliance under the prior interpretation, and the availability of less drastic alternatives (such as a compliance schedule) renders the decision arbitrary. We remand for the EPA to reconsider with due regard for reliance interests, without prejudging the outcome."""
    },
    {
        "case_name": "Foster v. Meridian Health Insurance Co.",
        "citation": "234 F.4th 567 (3d Cir. 2021)",
        "court": "United States Court of Appeals, Third Circuit",
        "date": "2021-05-15",
        "summary": "Health insurer's denial of mental health coverage at lower reimbursement rates than physical health violated the Mental Health Parity Act.",
        "full_text": """FOSTER v. MERIDIAN HEALTH INSURANCE CO.
234 F.4th 567 (3d Cir. 2021)

OPINION: Plaintiff David Foster challenges Meridian Health Insurance Company's denial of coverage for intensive outpatient mental health treatment and its systematic reimbursement of mental health services at lower rates than comparable physical health services.

Foster's plan covers intensive outpatient treatment for physical conditions (such as cardiac rehabilitation and physical therapy) at 80% of the reasonable and customary rate. Mental health intensive outpatient treatment is covered at only 50%, with additional prior authorization requirements not imposed on physical health treatment.

Meridian argues that the differential treatment reflects actuarial differences between mental and physical health services.

HELD: Meridian's coverage scheme violates the Mental Health Parity and Addiction Equity Act (MHPAEA), 29 U.S.C. § 1185a. The Act requires that financial requirements and treatment limitations applicable to mental health benefits be no more restrictive than the predominant requirements applied to substantially all medical and surgical benefits.

The 50% reimbursement rate for mental health versus 80% for physical health is a facially disparate financial requirement. The additional prior authorization requirement for mental health services is a more restrictive treatment limitation. Meridian's actuarial justification does not satisfy the MHPAEA's requirements; the statute specifically prohibits using actuarial differences to justify disparate treatment. Judgment for Foster; Meridian must reprocess all affected claims at parity rates."""
    },
    {
        "case_name": "Chen v. GigWork Platform Inc.",
        "citation": "567 P.3d 890 (Cal. 2022)",
        "court": "Supreme Court of California",
        "date": "2022-01-30",
        "summary": "Gig workers classified as employees under ABC test; platform's control over pricing and customer relationships was determinative.",
        "full_text": """CHEN v. GIGWORK PLATFORM INC.
567 P.3d 890 (Cal. 2022)

OPINION: This case requires us to apply the ABC test adopted in Dynamex Operations West, Inc. v. Superior Court, 4 Cal.5th 903 (2018), to determine whether delivery drivers for GigWork Platform Inc. are employees or independent contractors.

GigWork operates a food delivery platform. Drivers use their own vehicles and set their own hours. However, GigWork sets delivery prices, assigns orders through its algorithm, rates drivers on performance metrics, and prohibits drivers from soliciting direct business from restaurants or customers on the platform.

Under the ABC test, a worker is an employee unless the hiring entity establishes: (A) the worker is free from the control and direction of the hirer, (B) the worker performs work outside the usual course of the hiring entity's business, and (C) the worker is customarily engaged in an independently established trade or occupation.

HELD: The drivers are employees. GigWork fails all three prongs. On prong A, while drivers choose their hours, GigWork controls pricing, customer assignments, and performance evaluation — the core economic terms of the relationship. On prong B, delivery is GigWork's entire business; the drivers' work is not outside GigWork's usual course of business. On prong C, most drivers work exclusively or primarily for GigWork and do not maintain independent delivery businesses.

The classification as employees entitles the drivers to minimum wage, overtime, expense reimbursement, and other employment protections under the Labor Code."""
    },
    {
        "case_name": "United States v. Hargrove",
        "citation": "890 F.3d 234 (4th Cir. 2020)",
        "court": "United States Court of Appeals, Fourth Circuit",
        "date": "2020-10-22",
        "summary": "Geofence warrant seeking location data for all persons near a crime scene was overbroad and violated the Fourth Amendment.",
        "full_text": """UNITED STATES v. HARGROVE
890 F.3d 234 (4th Cir. 2020)

OPINION: Defendant Anthony Hargrove moves to suppress evidence obtained through a geofence warrant issued to Google, seeking location history data for all users whose devices were within a 500-meter radius of a bank robbery for a two-hour window.

The warrant returned data on 147 individuals. Through progressive narrowing, law enforcement identified Hargrove as a suspect. Hargrove was convicted based in part on the location data.

HELD: The geofence warrant violated the Fourth Amendment. While the Supreme Court in Carpenter v. United States, 585 U.S. 296 (2018), recognized a reasonable expectation of privacy in historical cell-site location information, the geofence warrant at issue goes further: it conducts a search of every person in a geographic area, the vast majority of whom have no connection to the crime.

A geofence warrant effectively conducts a general search — the very evil the Fourth Amendment was designed to prevent. It searches first and identifies suspects second, inverting the constitutional requirement that a warrant be supported by probable cause to search a particular person or place. The 147 innocent individuals whose location data was swept up had a reasonable expectation of privacy in their movements.

We hold that geofence warrants, as currently structured, are constitutionally deficient. The evidence is suppressed."""
    },
    {
        "case_name": "Riverdale Tenants Association v. Sterling Properties",
        "citation": "123 A.D.3d 456 (N.Y. App. Div. 2021)",
        "court": "New York Supreme Court, Appellate Division",
        "date": "2021-08-12",
        "summary": "Landlord's failure to provide adequate heat during winter months constituted constructive eviction; tenants entitled to rent abatement.",
        "full_text": """RIVERDALE TENANTS ASSOCIATION v. STERLING PROPERTIES
123 A.D.3d 456 (N.Y. App. Div. 2021)

OPINION: The Riverdale Tenants Association, representing 45 tenants of a 60-unit residential building, brings this action against Sterling Properties for constructive eviction and breach of the warranty of habitability.

From November 2020 through February 2021, the building's heating system operated at reduced capacity, resulting in indoor temperatures frequently below 55 degrees Fahrenheit during nighttime hours. City housing inspectors documented the violations on six occasions. Sterling Properties acknowledged the heating deficiency but claimed financial hardship prevented immediate repair of the boiler system.

HELD: Sterling Properties' failure to maintain adequate heat constitutes both a breach of the warranty of habitability under Real Property Law § 235-b and constructive eviction. The warranty of habitability is non-waivable and requires landlords to maintain residential premises in a condition fit for human habitation. Indoor temperatures below the legally mandated minimum (68°F during the day, 62°F at night when outdoor temperatures fall below 55°F) represent a clear violation.

Financial hardship does not excuse a landlord's obligation to maintain habitable conditions. Tenants are entitled to a rent abatement of 40% for the four-month period of inadequate heat, totaling $216,000 across the affected units. Sterling Properties is further ordered to complete boiler repairs within 30 days."""
    },
    {
        "case_name": "Quantum Dynamics Corp. v. Former Officers",
        "citation": "456 Del.Ch. 789 (2021)",
        "court": "Delaware Court of Chancery",
        "date": "2021-11-05",
        "summary": "Corporate officers breached fiduciary duty of loyalty by diverting business opportunities to competing entity they secretly controlled.",
        "full_text": """QUANTUM DYNAMICS CORP. v. FORMER OFFICERS
456 Del.Ch. 789 (2021)

OPINION: Quantum Dynamics Corp. brings this derivative action against its former CEO, Thomas Reed, and former CTO, Lisa Park, alleging breach of fiduciary duties.

While still employed at Quantum Dynamics, Reed and Park secretly formed NovaTech LLC and began redirecting potential client contracts to NovaTech. Over an 18-month period, NovaTech secured $3.2 million in contracts from clients who had initially approached Quantum Dynamics. Reed and Park did not disclose their interest in NovaTech to Quantum Dynamics' board.

The defendants argue that the diverted opportunities were outside Quantum Dynamics' line of business and that the company lacked the financial ability to exploit them.

HELD: Reed and Park breached their fiduciary duty of loyalty. Under the corporate opportunity doctrine as articulated in Guth v. Loft, Inc., 5 A.2d 503 (Del. 1939), a corporate officer may not seize for personal benefit a business opportunity that belongs to the corporation. An opportunity belongs to the corporation if: (1) the corporation is financially able to exploit it, (2) the opportunity is within the corporation's line of business, (3) the corporation has an interest or expectancy in it, and (4) taking the opportunity would create a conflict with the officer's duties.

All four factors are met here. The opportunities came through Quantum Dynamics' existing client relationships. The defendants' concealment of their competing entity compounds the breach. Judgment for Quantum Dynamics; disgorgement of $3.2 million in profits plus attorneys' fees."""
    },
]


def seed_database():
    Base.metadata.create_all(engine)
    db = SessionLocal()
    try:
        existing = db.query(CaseCorpus).count()
        if existing > 0:
            print(f"Database already has {existing} cases. Skipping seed.")
            return

        for case_data in SEED_CASES:
            case = CaseCorpus(**case_data)
            db.add(case)
        db.commit()
        print(f"Seeded {len(SEED_CASES)} cases into the database.")

        cases = db.query(CaseCorpus).all()
        for case in cases:
            chunks = _chunk_text(case.full_text, chunk_size=500, overlap=100)
            for chunk in chunks:
                emb = CaseEmbedding(case_id=case.id, chunk_text=chunk)
                db.add(emb)
        db.commit()
        print("Created case embedding chunk records.")
    finally:
        db.close()


def _chunk_text(text: str, chunk_size: int = 500, overlap: int = 100) -> list[str]:
    words = text.split()
    chunks = []
    start = 0
    while start < len(words):
        end = start + chunk_size
        chunk = " ".join(words[start:end])
        chunks.append(chunk)
        start = end - overlap
    return chunks


if __name__ == "__main__":
    seed_database()
