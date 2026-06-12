import Nav from '@/components/manifesto/Nav'
import MotionRoot from '@/components/fx/MotionRoot'
import WaterCursor from '@/components/fx/WaterCursor'
import S01_Hero from '@/components/manifesto/S01_Hero'
import S02_Problem from '@/components/manifesto/S02_Problem'
import S03_Pipeline from '@/components/manifesto/S03_Pipeline'
import S04_Maya from '@/components/manifesto/S04_Maya'
import S05_Aria from '@/components/manifesto/S05_Aria'
import S06_Rex from '@/components/manifesto/S06_Rex'
import S07_Zen from '@/components/manifesto/S07_Zen'
import S08_Marcus from '@/components/manifesto/S08_Marcus'
import S09_Lexi from '@/components/manifesto/S09_Lexi'
import S10_Kira from '@/components/manifesto/S10_Kira'
import S11_Proof from '@/components/manifesto/S11_Proof'
import S12_Loop from '@/components/manifesto/S12_Loop'
import S13_CTA from '@/components/manifesto/S13_CTA'

export default function Home() {
  return (
    <MotionRoot>
      <WaterCursor />
      <Nav />
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
