export type ArtifactType = 'CONTRACT' | 'SPEC' | 'EMAIL' | 'PROPOSAL'
export type ArtifactStatus = 'APPROVED' | 'PENDING' | 'REJECTED'

export type Artifact = {
  id: string
  type: ArtifactType
  title: string
  agent: string
  date: string
  status: ArtifactStatus
  body: string
}

export const ARTIFACTS: Artifact[] = [
  {
    id: 'nda-priya', type: 'CONTRACT', title: 'NDA — Priya Fintech', agent: 'ContractForge', date: 'JUL 16', status: 'PENDING',
    body: 'MUTUAL NON-DISCLOSURE AGREEMENT\n\nThis Agreement is made under the Indian Contract Act, 1872, between Priya Fintech Pvt. Ltd. ("Disclosing Party") and the Receiving Party, governed by the laws of India with exclusive jurisdiction in Mumbai...',
  },
  {
    id: 'service-rahul', type: 'CONTRACT', title: 'Service Agreement — Rahul', agent: 'ContractForge', date: 'JUL 15', status: 'APPROVED',
    body: 'SERVICE AGREEMENT\n\nThis Service Agreement is entered into between Rahul Devtools and the Service Provider. GST at 18% applies to all invoiced amounts. Jurisdiction: Mumbai, Maharashtra...',
  },
  {
    id: 'invoiceforge-spec', type: 'SPEC', title: 'InvoiceForge — Spec v0.3', agent: 'SpecForge', date: 'JUL 15', status: 'PENDING',
    body: 'PRODUCT SPEC: InvoiceForge\n\nStage 03/18 — Spec Generation. Target market: Indian SMBs. Core loop: invoice creation → GST calculation → payment tracking...',
  },
  {
    id: 'outreach-ca-04', type: 'EMAIL', title: 'Outreach — CA Firm Batch 04', agent: 'OutreachForge', date: 'JUL 14', status: 'APPROVED',
    body: 'Subject: Cut contract drafting time by 90%\n\nHi {{first_name}}, I noticed your firm handles freelancer onboarding for several clients. ContractForge generates GST-compliant contracts in 60 seconds...',
  },
  {
    id: 'proposal-rahul', type: 'PROPOSAL', title: 'Proposal — Rahul Devtools', agent: 'ClientForge', date: 'JUL 14', status: 'APPROVED',
    body: 'PROJECT PROPOSAL\n\nScope: custom API integration for Rahul Devtools. Timeline: 2 weeks. Deliverables: authenticated REST endpoints, webhook relay, documentation...',
  },
  {
    id: 'clientforge-rules', type: 'SPEC', title: 'ClientForge Pipeline Rules', agent: 'GBrain', date: 'JUL 13', status: 'APPROVED',
    body: 'GBRAIN NIGHTLY LOOP OUTPUT\n\nPattern detected: proposals sent within 2 hours of first contact convert at 3.1x the rate of same-day-but-delayed proposals. Rule proposed: escalate ClientForge proposal drafts to priority queue...',
  },
  {
    id: 'followup-ananya', type: 'EMAIL', title: 'Follow-up — @ananya_saas', agent: 'OutreachForge', date: 'JUL 13', status: 'REJECTED',
    body: 'Subject: Following up\n\nHi Ananya, just checking in on the ContractForge demo — REJECTED: tone flagged as too aggressive by founder review, redraft required...',
  },
  {
    id: 'freelance-template', type: 'CONTRACT', title: 'Freelance Agreement Template', agent: 'ContractForge', date: 'JUL 12', status: 'APPROVED',
    body: 'FREELANCE SERVICE AGREEMENT — TEMPLATE\n\nGoverned by the Indian Contract Act, 1872. GST 18% where applicable. Includes standard IP assignment and confidentiality clauses for Indian freelance engagements...',
  },
]

export const TYPE_COLOR: Record<ArtifactType, string> = {
  CONTRACT: '#A4D8FF',
  SPEC: 'rgba(164,216,255,0.75)',
  EMAIL: 'rgba(164,216,255,0.60)',
  PROPOSAL: 'rgba(164,216,255,0.55)',
}

export const STATUS_COLOR: Record<ArtifactStatus, string> = {
  APPROVED: '#A4D8FF',
  PENDING: 'rgba(236,235,230,0.45)',
  REJECTED: 'var(--error)',
}
