"""
Built-in curriculum: AWS Certified Cloud Practitioner (CLF-C02).

This is the example goal from the product brief. It is a hand-authored knowledge
base the content engine uses to produce lessons, examples, quizzes and flashcards.
Each topic carries:
  * lesson sections (title + markdown-ish body)
  * worked examples
  * quiz questions (multiple choice, with explanations)
  * flashcards (front/back)
Difficulty is 1 (intro) .. 3 (advanced). `base_minutes` is the nominal study time
for a learner at "beginner" level; the planner scales it by level.
"""

CURRICULUM = {
    "id": "aws-clf-c02",
    "title": "AWS Certified Cloud Practitioner (CLF-C02)",
    "summary": "Foundational AWS certification covering cloud concepts, security, "
               "core services, billing and the AWS Well-Architected mindset.",
    "domains": [
        "Cloud Concepts",
        "Security & Compliance",
        "Cloud Technology & Services",
        "Billing, Pricing & Support",
    ],
    "topics": [
        # ---------------- Cloud Concepts ----------------
        {
            "id": "what-is-cloud",
            "domain": "Cloud Concepts",
            "title": "What Is Cloud Computing?",
            "difficulty": 1,
            "base_minutes": 35,
            "objective": "Explain cloud computing and the AWS value proposition.",
            "lesson": [
                {"heading": "The core idea",
                 "body": "Cloud computing is the on-demand delivery of IT resources—compute, "
                         "storage, databases, networking—over the internet, with pay-as-you-go "
                         "pricing. Instead of buying and running your own data center, you rent "
                         "exactly what you need from a provider like AWS and give it back when "
                         "you're done."},
                {"heading": "Six advantages of cloud",
                 "body": "AWS frames the benefits as six points you should memorize:\n"
                         "1. Trade capital expense (CapEx) for variable expense (OpEx).\n"
                         "2. Benefit from massive economies of scale.\n"
                         "3. Stop guessing capacity — scale up and down on demand.\n"
                         "4. Increase speed and agility — resources in minutes, not weeks.\n"
                         "5. Stop spending money running and maintaining data centers.\n"
                         "6. Go global in minutes."},
                {"heading": "Three deployment models",
                 "body": "Cloud (everything runs in the cloud), Hybrid (cloud + on-premises "
                         "connected together), and On-premises / private cloud (your own data "
                         "center, sometimes called 'private cloud' when virtualized)."},
            ],
            "examples": [
                {"title": "CapEx vs OpEx in practice",
                 "body": "A startup expecting unknown traffic launches on EC2. Instead of "
                         "buying $200k of servers up front (CapEx), it pays ~$0.10/hour per "
                         "instance (OpEx) and scales to zero overnight. If the product flops, "
                         "they stop paying immediately."},
            ],
            "quiz": [
                {"q": "Which is an example of trading capital expense for variable expense?",
                 "choices": ["Buying servers for a 3-year plan",
                             "Paying only for EC2 compute hours you actually use",
                             "Signing a data-center lease",
                             "Hiring a facilities team"],
                 "answer": 1,
                 "explain": "Pay-as-you-go EC2 usage is variable (operational) expense; buying "
                            "hardware up front is capital expense."},
                {"q": "'Stop guessing capacity' is possible on AWS mainly because of…",
                 "choices": ["Fixed server quotas", "Elastic, on-demand scaling",
                             "Annual hardware orders", "Manual provisioning tickets"],
                 "answer": 1,
                 "explain": "Elasticity lets you scale resources up and down to match demand."},
            ],
            "flashcards": [
                {"front": "Define cloud computing in one sentence.",
                 "back": "On-demand delivery of IT resources over the internet with "
                         "pay-as-you-go pricing."},
                {"front": "Name 3 of the six advantages of cloud.",
                 "back": "CapEx→OpEx, economies of scale, stop guessing capacity, speed/agility, "
                         "no data-center maintenance, go global in minutes (any 3)."},
                {"front": "What are the three cloud deployment models?",
                 "back": "Cloud, Hybrid, and On-premises (private cloud)."},
            ],
        },
        {
            "id": "regions-az",
            "domain": "Cloud Concepts",
            "title": "Regions, Availability Zones & Edge Locations",
            "difficulty": 1,
            "base_minutes": 30,
            "objective": "Describe AWS global infrastructure and when to use each layer.",
            "lesson": [
                {"heading": "Regions",
                 "body": "A Region is a physical geographic area (e.g. us-east-1). You choose a "
                         "Region for latency to users, data-sovereignty/compliance, service "
                         "availability, and pricing."},
                {"heading": "Availability Zones (AZs)",
                 "body": "Each Region has multiple AZs — one or more discrete data centers with "
                         "independent power, cooling and networking, physically separated but "
                         "linked by low-latency fiber. Deploying across AZs gives high "
                         "availability: if one AZ fails, others keep serving."},
                {"heading": "Edge locations",
                 "body": "Hundreds of edge locations cache content close to users for services "
                         "like CloudFront (CDN) and Route 53, reducing latency globally."},
            ],
            "examples": [
                {"title": "Designing for an AZ failure",
                 "body": "You run two EC2 web servers in us-east-1a and us-east-1b behind an "
                         "Elastic Load Balancer. If us-east-1a has an outage, the load balancer "
                         "routes all traffic to us-east-1b and users barely notice."},
            ],
            "quiz": [
                {"q": "What is the main reason to deploy across multiple Availability Zones?",
                 "choices": ["Lower cost", "High availability / fault isolation",
                             "Simpler networking", "To use edge caching"],
                 "answer": 1,
                 "explain": "AZs are isolated failure domains; spreading across them survives a "
                            "single-AZ outage."},
                {"q": "Which service uses edge locations to cache content near users?",
                 "choices": ["Amazon RDS", "Amazon CloudFront", "AWS IAM", "Amazon EBS"],
                 "answer": 1,
                 "explain": "CloudFront is AWS's CDN and serves cached content from edge locations."},
            ],
            "flashcards": [
                {"front": "Region vs Availability Zone?",
                 "back": "A Region is a geographic area; an AZ is one or more isolated data "
                         "centers within a Region."},
                {"front": "Why deploy across multiple AZs?",
                 "back": "Fault isolation / high availability — survive a single-AZ outage."},
                {"front": "What are edge locations used for?",
                 "back": "Caching content close to users (CloudFront CDN, Route 53) to cut latency."},
            ],
        },
        {
            "id": "shared-responsibility",
            "domain": "Security & Compliance",
            "title": "The Shared Responsibility Model",
            "difficulty": 2,
            "base_minutes": 30,
            "objective": "Distinguish what AWS secures vs what the customer secures.",
            "lesson": [
                {"heading": "Security OF vs IN the cloud",
                 "body": "AWS is responsible for security OF the cloud: the hardware, the global "
                         "infrastructure, the hypervisor, and managed-service internals. The "
                         "customer is responsible for security IN the cloud: their data, "
                         "identity & access (IAM), OS patching on EC2, network config, and "
                         "encryption choices."},
                {"heading": "It shifts by service type",
                 "body": "The line moves depending on the service. On EC2 (IaaS) you patch the "
                         "guest OS. On RDS (managed) AWS patches the DB engine but you still "
                         "manage users and data. On S3 you configure access policies and "
                         "encryption; AWS runs the storage substrate."},
            ],
            "examples": [
                {"title": "Who patches what?",
                 "body": "A public S3 bucket leaks data. That's a CUSTOMER failure — bucket "
                         "policy/ACL is 'security in the cloud'. A hypervisor vulnerability is "
                         "AWS's responsibility — 'security of the cloud'."},
            ],
            "quiz": [
                {"q": "Under the shared responsibility model, who patches the guest OS on an "
                      "EC2 instance?",
                 "choices": ["AWS", "The customer", "Nobody — it's automatic",
                             "The AWS Marketplace vendor"],
                 "answer": 1,
                 "explain": "On EC2 (IaaS) the customer manages and patches the guest OS."},
                {"q": "Which is AWS's responsibility?",
                 "choices": ["IAM user passwords", "Physical data-center security",
                             "S3 bucket policies", "Application code"],
                 "answer": 1,
                 "explain": "Physical infrastructure is 'security OF the cloud' = AWS."},
            ],
            "flashcards": [
                {"front": "Security OF the cloud vs IN the cloud — who owns each?",
                 "back": "OF the cloud = AWS (hardware, global infra). IN the cloud = customer "
                         "(data, IAM, OS patching, config)."},
                {"front": "On EC2, who patches the guest OS?",
                 "back": "The customer."},
                {"front": "On RDS, who patches the database engine?",
                 "back": "AWS (it's a managed service), but the customer still manages users/data."},
            ],
        },
        {
            "id": "iam",
            "domain": "Security & Compliance",
            "title": "Identity & Access Management (IAM)",
            "difficulty": 2,
            "base_minutes": 40,
            "objective": "Explain IAM users, groups, roles, policies and best practices.",
            "lesson": [
                {"heading": "The building blocks",
                 "body": "Users (a person or app), Groups (a set of users sharing permissions), "
                         "Roles (temporary credentials assumed by services or users), and "
                         "Policies (JSON documents granting/denying actions on resources)."},
                {"heading": "Least privilege & MFA",
                 "body": "Grant only the permissions needed (least privilege). Enable "
                         "Multi-Factor Authentication, especially on the root account. Never use "
                         "the root user for daily work; create individual IAM users or federate."},
                {"heading": "Roles vs users",
                 "body": "Use roles for machine-to-machine and cross-account access — they issue "
                         "short-lived credentials, so there are no long-term keys to leak. An "
                         "EC2 instance should get S3 access via an instance role, not a hardcoded "
                         "access key."},
            ],
            "examples": [
                {"title": "Instance role instead of keys",
                 "body": "An app on EC2 needs to read from S3. Instead of baking an access key "
                         "into the code, you attach an IAM role to the instance. AWS rotates the "
                         "temporary credentials automatically — nothing to leak."},
            ],
            "quiz": [
                {"q": "What is the recommended way to give an EC2 app access to S3?",
                 "choices": ["Hardcode an access key", "Attach an IAM role to the instance",
                             "Use the root account", "Make the bucket public"],
                 "answer": 1,
                 "explain": "IAM roles provide auto-rotating temporary credentials with no keys "
                            "to leak."},
                {"q": "Which principle says to grant only the permissions actually needed?",
                 "choices": ["Defense in depth", "Least privilege", "Shared responsibility",
                             "Zero trust networking"],
                 "answer": 1,
                 "explain": "Least privilege minimizes blast radius if credentials are misused."},
            ],
            "flashcards": [
                {"front": "IAM: user vs group vs role?",
                 "back": "User = identity for a person/app; Group = permission set for many "
                         "users; Role = assumable identity with temporary credentials."},
                {"front": "Why prefer IAM roles over access keys for services?",
                 "back": "Roles issue short-lived, auto-rotated credentials — no long-term keys "
                         "to leak."},
                {"front": "What does 'least privilege' mean?",
                 "back": "Grant only the minimum permissions required to do the job."},
            ],
        },
        {
            "id": "compute-ec2",
            "domain": "Cloud Technology & Services",
            "title": "Core Compute: EC2, Lambda & Containers",
            "difficulty": 2,
            "base_minutes": 45,
            "objective": "Compare EC2, Lambda, and container services and when to use each.",
            "lesson": [
                {"heading": "EC2 — virtual servers",
                 "body": "Elastic Compute Cloud gives you resizable virtual machines. You pick "
                         "an instance type (CPU/RAM), an AMI (image), and pay per second/hour. "
                         "You manage the OS. Best when you need full control or run traditional "
                         "server software."},
                {"heading": "Lambda — serverless functions",
                 "body": "Run code without managing servers. You upload a function; AWS runs it "
                         "on each event and bills per millisecond of execution. Scales to zero. "
                         "Best for event-driven, spiky, or short-lived workloads."},
                {"heading": "Containers — ECS, EKS, Fargate",
                 "body": "ECS and EKS (Kubernetes) orchestrate Docker containers. Fargate runs "
                         "containers serverlessly (no EC2 to manage). Best for microservices and "
                         "portable workloads."},
            ],
            "examples": [
                {"title": "Choosing compute",
                 "body": "A nightly report that runs for 20 seconds → Lambda (pay only for those "
                         "seconds). A 24/7 legacy Java monolith → EC2. A fleet of microservices "
                         "→ ECS/EKS on Fargate."},
            ],
            "quiz": [
                {"q": "Which service is best for a short, event-driven job that runs occasionally?",
                 "choices": ["EC2 reserved instance", "AWS Lambda", "A dedicated host",
                             "Amazon EBS"],
                 "answer": 1,
                 "explain": "Lambda scales to zero and bills per millisecond — ideal for spiky, "
                            "short jobs."},
                {"q": "What does AWS Fargate let you do?",
                 "choices": ["Run containers without managing servers",
                             "Store objects cheaply", "Cache DNS", "Encrypt EBS volumes"],
                 "answer": 0,
                 "explain": "Fargate runs containers serverlessly — no EC2 hosts to manage."},
            ],
            "flashcards": [
                {"front": "When would you choose Lambda over EC2?",
                 "back": "Event-driven, spiky, or short-lived workloads where you want "
                         "pay-per-use and no server management."},
                {"front": "What is AWS Fargate?",
                 "back": "A serverless way to run containers (ECS/EKS) with no EC2 hosts to manage."},
                {"front": "What do you manage on EC2 that you don't on Lambda?",
                 "back": "The operating system, scaling, and the running server itself."},
            ],
        },
        {
            "id": "storage-s3",
            "domain": "Cloud Technology & Services",
            "title": "Storage: S3, EBS & EFS",
            "difficulty": 2,
            "base_minutes": 40,
            "objective": "Differentiate object, block and file storage and S3 storage classes.",
            "lesson": [
                {"heading": "Three storage types",
                 "body": "Object storage (S3): store files as objects in buckets, accessed over "
                         "HTTP, virtually unlimited. Block storage (EBS): disk volumes attached "
                         "to a single EC2 instance. File storage (EFS/FSx): a shared filesystem "
                         "many instances can mount."},
                {"heading": "S3 storage classes",
                 "body": "Standard (frequent access), Standard-IA / One Zone-IA (infrequent), "
                         "Glacier Instant/Flexible/Deep Archive (cheap, archival, slower "
                         "retrieval), and Intelligent-Tiering (auto-moves data between tiers to "
                         "save cost)."},
                {"heading": "Durability",
                 "body": "S3 is designed for 11 nines (99.999999999%) of durability by "
                         "replicating objects across multiple devices and AZs."},
            ],
            "examples": [
                {"title": "Matching data to a storage class",
                 "body": "Website images served constantly → S3 Standard. Monthly backups you "
                         "rarely read → Standard-IA. Compliance archives kept 7 years and almost "
                         "never read → Glacier Deep Archive."},
            ],
            "quiz": [
                {"q": "Which storage type is attached to a single EC2 instance like a disk?",
                 "choices": ["S3", "EBS", "EFS", "CloudFront"],
                 "answer": 1,
                 "explain": "EBS provides block storage volumes attached to one instance."},
                {"q": "Where would you store rarely accessed 7-year compliance archives most "
                      "cheaply?",
                 "choices": ["S3 Standard", "EBS", "S3 Glacier Deep Archive", "EFS"],
                 "answer": 2,
                 "explain": "Glacier Deep Archive is the lowest-cost class for long-term, "
                            "rarely-read data."},
            ],
            "flashcards": [
                {"front": "Object vs block vs file storage on AWS — name a service for each.",
                 "back": "Object = S3, Block = EBS, File = EFS (or FSx)."},
                {"front": "What durability is S3 designed for?",
                 "back": "11 nines — 99.999999999%."},
                {"front": "Which S3 class auto-moves data to cheaper tiers?",
                 "back": "S3 Intelligent-Tiering."},
            ],
        },
        {
            "id": "databases",
            "domain": "Cloud Technology & Services",
            "title": "Databases: RDS, DynamoDB & Aurora",
            "difficulty": 2,
            "base_minutes": 35,
            "objective": "Contrast relational vs NoSQL managed databases on AWS.",
            "lesson": [
                {"heading": "Relational (SQL) — RDS & Aurora",
                 "body": "Amazon RDS manages relational engines (MySQL, PostgreSQL, SQL Server, "
                         "Oracle, MariaDB): AWS handles patching, backups, and failover. Aurora "
                         "is AWS's high-performance MySQL/PostgreSQL-compatible engine."},
                {"heading": "NoSQL — DynamoDB",
                 "body": "DynamoDB is a fully managed key-value / document database with "
                         "single-digit-millisecond latency and seamless scaling. No servers to "
                         "manage; great for high-traffic, flexible-schema workloads."},
            ],
            "examples": [
                {"title": "SQL vs NoSQL choice",
                 "body": "An accounting system with complex joins and transactions → RDS "
                         "(relational). A gaming leaderboard with millions of key lookups per "
                         "second → DynamoDB (NoSQL)."},
            ],
            "quiz": [
                {"q": "Which AWS service is a fully managed NoSQL database?",
                 "choices": ["Amazon RDS", "Amazon DynamoDB", "Amazon Aurora", "Amazon Redshift"],
                 "answer": 1,
                 "explain": "DynamoDB is AWS's managed NoSQL key-value/document store."},
                {"q": "What does Amazon RDS primarily manage for you?",
                 "choices": ["Your application code", "Relational DB patching, backups & failover",
                             "Object storage", "DNS routing"],
                 "answer": 1,
                 "explain": "RDS automates relational database administration tasks."},
            ],
            "flashcards": [
                {"front": "RDS vs DynamoDB — relational or NoSQL?",
                 "back": "RDS = managed relational (SQL). DynamoDB = managed NoSQL "
                         "(key-value/document)."},
                {"front": "What is Amazon Aurora?",
                 "back": "AWS's high-performance MySQL/PostgreSQL-compatible relational engine."},
                {"front": "When pick DynamoDB over RDS?",
                 "back": "High-scale, flexible-schema, key lookups needing single-digit-ms latency."},
            ],
        },
        {
            "id": "pricing",
            "domain": "Billing, Pricing & Support",
            "title": "Pricing Models & Cost Management",
            "difficulty": 2,
            "base_minutes": 40,
            "objective": "Explain EC2 purchasing options and AWS cost-management tools.",
            "lesson": [
                {"heading": "EC2 purchasing options",
                 "body": "On-Demand (pay per use, no commitment, most flexible), Reserved "
                         "Instances / Savings Plans (1–3 yr commitment for big discounts), Spot "
                         "Instances (up to ~90% off spare capacity, can be reclaimed), and "
                         "Dedicated Hosts (physical server for licensing/compliance)."},
                {"heading": "Cost tools",
                 "body": "AWS Pricing Calculator (estimate before you build), Cost Explorer "
                         "(visualize and forecast spend), AWS Budgets (alerts when you exceed a "
                         "threshold), and Cost Allocation Tags (attribute costs to teams/projects)."},
                {"heading": "Free Tier",
                 "body": "Three types: Always Free (e.g. Lambda 1M requests/mo), 12-months-free "
                         "(e.g. 750 EC2 t2.micro hours/mo for new accounts), and trials."},
            ],
            "examples": [
                {"title": "Matching workload to pricing",
                 "body": "Steady 24/7 baseline → Reserved/Savings Plan. Unpredictable bursts → "
                         "On-Demand. Fault-tolerant batch processing → Spot (cheapest, but can be "
                         "interrupted)."},
            ],
            "quiz": [
                {"q": "Which EC2 option offers the deepest discount but can be reclaimed by AWS?",
                 "choices": ["On-Demand", "Reserved Instance", "Spot Instance", "Dedicated Host"],
                 "answer": 2,
                 "explain": "Spot uses spare capacity at up to ~90% off but can be interrupted."},
                {"q": "Which tool alerts you when spending exceeds a threshold?",
                 "choices": ["Cost Explorer", "AWS Budgets", "Pricing Calculator",
                             "Trusted Advisor"],
                 "answer": 1,
                 "explain": "AWS Budgets sends alerts when actual or forecast cost crosses a limit."},
            ],
            "flashcards": [
                {"front": "Name the four main EC2 purchasing options.",
                 "back": "On-Demand, Reserved/Savings Plans, Spot, and Dedicated Hosts."},
                {"front": "Which EC2 option is cheapest but interruptible?",
                 "back": "Spot Instances (up to ~90% off, can be reclaimed)."},
                {"front": "Which tool sends alerts when you exceed a spending threshold?",
                 "back": "AWS Budgets."},
            ],
        },
        {
            "id": "support-well-architected",
            "domain": "Billing, Pricing & Support",
            "title": "Support Plans & The Well-Architected Framework",
            "difficulty": 1,
            "base_minutes": 30,
            "objective": "Identify AWS support tiers and the Well-Architected pillars.",
            "lesson": [
                {"heading": "Support plans",
                 "body": "Basic (free: docs, forums, Trusted Advisor core checks), Developer "
                         "(business-hours email), Business (24/7 phone/chat, faster SLAs, full "
                         "Trusted Advisor), and Enterprise / Enterprise On-Ramp (a Technical "
                         "Account Manager, fastest response)."},
                {"heading": "The six Well-Architected pillars",
                 "body": "Operational Excellence, Security, Reliability, Performance Efficiency, "
                         "Cost Optimization, and Sustainability. They are the design principles "
                         "AWS recommends for building sound cloud systems."},
            ],
            "examples": [
                {"title": "Which support plan?",
                 "body": "A company running production workloads needing 24/7 support with a "
                         "~1-hour response for production-down issues chooses the Business plan. "
                         "A large org wanting a dedicated TAM chooses Enterprise."},
            ],
            "quiz": [
                {"q": "Which support plan includes a dedicated Technical Account Manager (TAM)?",
                 "choices": ["Basic", "Developer", "Business", "Enterprise"],
                 "answer": 3,
                 "explain": "A dedicated TAM is an Enterprise (and Enterprise On-Ramp) benefit."},
                {"q": "Which is NOT one of the Well-Architected pillars?",
                 "choices": ["Security", "Reliability", "Marketing Efficiency",
                             "Cost Optimization"],
                 "answer": 2,
                 "explain": "The pillars are Operational Excellence, Security, Reliability, "
                            "Performance Efficiency, Cost Optimization, Sustainability."},
            ],
            "flashcards": [
                {"front": "List the six Well-Architected pillars.",
                 "back": "Operational Excellence, Security, Reliability, Performance Efficiency, "
                         "Cost Optimization, Sustainability."},
                {"front": "Which support plan includes a dedicated TAM?",
                 "back": "Enterprise (and Enterprise On-Ramp)."},
                {"front": "What does the free Basic support plan include?",
                 "back": "Docs, whitepapers, forums, and core Trusted Advisor checks."},
            ],
        },
    ],
}
