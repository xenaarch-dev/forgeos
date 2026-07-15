'use server'

import { createClient } from '@/lib/supabase/server'
import { redirect } from 'next/navigation'
import { validateStep } from '@/lib/onboarding/validate'

export async function completeOnboarding(formData: FormData) {
  const supabase = createClient()
  const { data: { user } } = await supabase.auth.getUser()
  if (!user) redirect('/login')

  const fullName = String(formData.get('fullName') ?? '').trim()
  const companyName = String(formData.get('companyName') ?? '').trim()

  const nameError = validateStep('name', fullName)
  if (nameError) {
    redirect(`/onboarding?error=${encodeURIComponent(nameError)}`)
  }
  if (companyName) {
    const companyError = validateStep('company', companyName)
    if (companyError) {
      redirect(`/onboarding?error=${encodeURIComponent(companyError)}`)
    }
  }

  let { data: workspace } = await supabase
    .from('workspaces')
    .select('id')
    .limit(1)
    .maybeSingle()

  if (!workspace) {
    const { data: created } = await supabase
      .from('workspaces')
      .insert({ name: companyName || 'My Workspace' })
      .select('id')
      .single()
    workspace = created
  }

  await supabase.from('profiles').upsert({
    id: user.id,
    workspace_id: workspace?.id ?? null,
    full_name: fullName || null,
    company_name: companyName || null,
    onboarded_at: new Date().toISOString(),
  })

  redirect('/app')
}

export async function skipOnboarding() {
  const supabase = createClient()
  const { data: { user } } = await supabase.auth.getUser()
  if (!user) redirect('/login')

  await supabase.from('profiles').upsert({
    id: user.id,
    onboarded_at: new Date().toISOString(),
  })

  redirect('/app')
}
