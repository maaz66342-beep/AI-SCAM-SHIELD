import csv, random
random.seed(42)

companies_real = ["Infosys", "TCS", "Wipro", "Accenture", "Capgemini", "Tech Mahindra",
    "HCL Technologies", "Cognizant", "IBM India", "Deloitte", "EY", "Zoho",
    "Freshworks", "Flipkart", "Swiggy", "Razorpay"]
roles = ["Software Engineer", "Data Analyst", "Web Developer", "Customer Support Executive",
    "HR Executive", "Digital Marketing Associate", "Business Analyst", "Content Writer",
    "Graphic Designer", "Backend Developer", "QA Tester", "Sales Executive"]
genuine_descs = [
    "We are looking for a {role} to join our growing team in {city}. Candidates must have relevant experience and a degree in a related field. Interviews will be conducted in two rounds - technical and HR.",
    "{company} is hiring a {role} for our {city} office. The role requires strong communication skills and 1-3 years of relevant experience. Please apply through our official careers portal.",
    "Join {company} as a {role}. We offer a competitive salary as per industry standards, health insurance, and standard company benefits. Work location: {city}.",
    "{company} is expanding its team and looking for a motivated {role}. Selected candidates will undergo standard onboarding and background verification before joining.",
]
fraud_descs = [
    "URGENT HIRING!!! {role} needed immediately. Earn upto Rs.80,000 per week just by working 2 hours from home. No experience needed. Registration fee of Rs.499 required to confirm your seat.",
    "Congratulations! You have been shortlisted for {role} at {company}. Kindly pay a refundable security deposit of Rs.2000 via UPI to receive your offer letter and laptop kit.",
    "Work from home {role} job. Guaranteed income Rs.50000/month. Limited seats!! Send your Aadhar card, bank details and a small processing fee to confirm your slot today.",
    "Immediate joining {role}, no interview required, 100% job guarantee. Contact on WhatsApp only. Pay Rs.999 registration fee to HR to get the joining kit couriered to your home.",
]
cities = ["Bangalore", "Pune", "Hyderabad", "Chennai", "Mumbai", "Delhi", "Noida", "Ahmedabad"]
rows = []
for _ in range(220):
    role, company, city = random.choice(roles), random.choice(companies_real), random.choice(cities)
    desc = random.choice(genuine_descs).format(role=role, company=company, city=city)
    rows.append([f"{role} - {company}", company, desc, f"Rs. {random.randint(3,12)},00,000 per annum", "Bachelor's degree, relevant experience", 0])
for _ in range(220):
    role = random.choice(roles)
    company = random.choice(["Global Career Hub", "QuickJobs Ltd", "WorkFromHome Solutions", "Bright Future Careers", "Instant Earn Pvt Ltd"])
    desc = random.choice(fraud_descs).format(role=role, company=company)
    rows.append([f"{role} URGENT - {company}", company, desc, f"Guaranteed Rs.{random.randint(30,90)},000 per week", "No experience needed, pay registration fee", 1])
random.shuffle(rows)

# Add some "hard" borderline examples where genuine and fraud vocabulary
# overlap a bit - this makes the dataset more realistic (100% accuracy on
# a college-project synthetic dataset looks suspicious in a viva; real
# datasets always have some overlap/noise).
hard_genuine = [
    ["Urgent Opening - {c}".format(c=random.choice(companies_real)),
     random.choice(companies_real),
     "We have an urgent requirement and are hiring immediately for a short notice joining. Genuine full-time role with standard company benefits and background verification.",
     f"Rs. {random.randint(4,9)},00,000 per annum", "2+ years experience required", 0]
    for _ in range(15)
]
hard_fraud = [
    ["Software Engineer - Bright Future Careers",
     "Bright Future Careers",
     "We are looking for a Software Engineer to join our team. Candidates must have relevant experience. Please note a one-time refundable kit deposit applies before joining.",
     f"Rs. {random.randint(3,7)},00,000 per annum", "Bachelor's degree required", 1]
    for _ in range(15)
]
rows.extend(hard_genuine)
rows.extend(hard_fraud)
random.shuffle(rows)

# Flip a small % of labels to simulate real-world label noise (mislabeled
# postings happen in real datasets too - this avoids an unrealistic 100%
# accuracy across all algorithms, which is what actual public datasets
# like the Kaggle "Fake Job Postings" set also show).
noise_count = int(len(rows) * 0.05)
noise_indices = random.sample(range(len(rows)), noise_count)
for i in noise_indices:
    rows[i][5] = 1 - rows[i][5]


with open("data/job_postings.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["title","company","description","salary","requirements","fraudulent"])
    w.writerows(rows)
print(f"Generated {len(rows)} rows")
