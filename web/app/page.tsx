import Nav from '@/components/portal/Nav'
import MotionRoot from '@/components/fx/MotionRoot'
import WaterCursor from '@/components/fx/WaterCursor'
import ProgressRail from '@/components/portal/ProgressRail'
import S01_Hero from '@/components/portal/S01_Hero'
import S02_Problem from '@/components/portal/S02_Problem'
import S03_Pipeline from '@/components/portal/S03_Pipeline'
import S04_Maya from '@/components/portal/S04_Maya'
import S05_Aria from '@/components/portal/S05_Aria'
import S06_Rex from '@/components/portal/S06_Rex'
import S07_Zen from '@/components/portal/S07_Zen'
import S08_Marcus from '@/components/portal/S08_Marcus'
import S09_Lexi from '@/components/portal/S09_Lexi'
import S10_Kira from '@/components/portal/S10_Kira'
import S11_Proof from '@/components/portal/S11_Proof'
import S12_Loop from '@/components/portal/S12_Loop'
import S13_CTA from '@/components/portal/S13_CTA'

export default function Home() {
  return (
    <MotionRoot>
      <WaterCursor />
      <Nav />
      <ProgressRail />
      <main>
        <S01_Hero />
        <S02_Problem />
        <S03_Pipeline />
        <S04_Maya />
        <S05_Aria />
        <S06_Rex />
        <S07_Zen />
        <S08_Marcus />
        <S09_Lexi />
        <S10_Kira />
        <S11_Proof />
        <S12_Loop />
        <S13_CTA />
      </main>
    </MotionRoot>
  )
}
