import Nav from '@/components/Nav'
import Hero from '@/components/Hero'
import ProofBar from '@/components/ProofBar'
import Pipeline from '@/components/Pipeline'
import AgentGrid from '@/components/AgentGrid'
import GBrainStrip from '@/components/GBrainStrip'
import HowItWorks from '@/components/HowItWorks'
import Footer from '@/components/Footer'

export default function Home() {
  return (
    <main>
      <Nav />
      <Hero />
      <ProofBar />
      <Pipeline />
      <AgentGrid />
      <GBrainStrip />
      <HowItWorks />
      <Footer />
    </main>
  )
}
