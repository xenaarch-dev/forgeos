# ContractForge — Known Bugs (QA 2026-05-26)

## MEDIUM

### [M1] Page title is "App" on all pages
- **Where**: Every page (layout.tsx or page.tsx metadata)
- **What**: `<title>App</title>` and `<meta name="description" content="Built with ForgeOS"/>` are ForgeOS scaffold placeholders — not ContractForge branding
- **Impact**: SEO damage, confusing browser tabs
- **Fix**: Update `metadata` export in `app/layout.tsx` and each page

## LOW

### [L1] Pricing page button labels inconsistent with landing page
- **Where**: `/pricing` page
- **What**: Buttons say "Buy Now" / "Subscribe" but landing page says "Buy single contract" / "Start monthly plan"
- **Fix**: Standardise to one set of labels across both pages

### [L2] "First contract always free" missing from /pricing
- **Where**: `/pricing` page
- **What**: Trust copy exists on the landing page but not on /pricing — users who land on /pricing directly get no free-tier reassurance
- **Fix**: Add below the plan cards, same as landing page

---
*Created by ComputerUseAgent QA session 2026-05-26*
*HIGH bug (Lemon Squeezy "Test mode active" label) fixed immediately — see commit*
