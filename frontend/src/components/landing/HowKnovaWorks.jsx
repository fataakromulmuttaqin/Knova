import { useEffect, useState } from 'react'
import pdfIcon from '../../assets/pdf-icon-clean.png'
import docxIcon from '../../assets/docx-icon-clean.png'
import mdIcon from '../../assets/md-icon-clean.png'

const STEPS = [
  {
    number: '01',
    title: 'Masukkan dokumennya.',
    text: 'Dokumen yang diunggah, halaman website, dan file Drive yang didukung masuk ke index khusus milik user.',
  },
  {
    number: '02',
    title: 'Temukan bagiannya.',
    text: 'Makna dan kata persis bertemu, lalu passage paling dekat yang dipakai.',
  },
  {
    number: '03',
    title: 'Tunjukkan buktinya.',
    text: 'Jawaban menyertakan sitasi yang membuka bukti hasil retrieval untuk diperiksa.',
  },
]

function BringScene({ on }) {
  return (
    <div className={`hw-scene hw-bring ${on ? 'is-on' : ''}`} aria-hidden="true">
      <img
        src={pdfIcon}
        alt="PDF"
        loading="lazy"
        decoding="async"
        className="hw-bring-doc"
        style={{ '--r': '-10deg', '--x': '0px' }}
      />
      <img
        src={docxIcon}
        alt="DOCX"
        loading="lazy"
        decoding="async"
        className="hw-bring-doc"
        style={{ '--r': '7deg', '--x': '18px' }}
      />
      <img
        src={mdIcon}
        alt="MD"
        loading="lazy"
        decoding="async"
        className="hw-bring-doc"
        style={{ '--r': '-3deg', '--x': '8px' }}
      />
    </div>
  )
}

function FindScene({ on }) {
  return (
    <div className={`hw-scene hw-find ${on ? 'is-on' : ''}`} aria-hidden="true">
      <p className="hw-find-q">Q3 pricing</p>
      <p className="hw-find-line">Wifi rotation schedule</p>
      <p className="hw-find-line is-hit">Usage-based billing for Q3</p>
      <p className="hw-find-line">Brand color tokens</p>
    </div>
  )
}

function ProofScene({ on }) {
  return (
    <div className={`hw-scene hw-proof ${on ? 'is-on' : ''}`} aria-hidden="true">
      <p>Usage-based billing was introduced for Q3.</p>
      <span>Q3 Report.pdf</span>
    </div>
  )
}

const SCENES = [BringScene, FindScene, ProofScene]

export default function HowKnovaWorks() {
  const [active, setActive] = useState(0)
  const [paused, setPaused] = useState(false)

  useEffect(() => {
    const motion = window.matchMedia('(prefers-reduced-motion: reduce)')
    if (motion.matches || paused) return undefined
    const id = window.setInterval(() => {
      setActive((current) => (current + 1) % STEPS.length)
    }, 3400)
    return () => window.clearInterval(id)
  }, [paused])

  return (
    <section id="how-it-works" className="how-it-works-section" data-nav-theme="light" aria-label="Cara Kerja KNOVA">
      <div className="how-it-works-inner">
        <header className="hw-head">
          <h2>Cara kerjanya.</h2>
          <p>Tiga langkah, dari file yang sudah kamu punya sampai jawaban yang bisa kamu cek.</p>
        </header>

        <div
          className="hw-grid"
          onMouseEnter={() => setPaused(true)}
          onMouseLeave={() => setPaused(false)}
        >
          {STEPS.map((step, index) => {
            const Scene = SCENES[index]
            const on = active === index
            return (
              <article
                key={step.number}
                className={`hw-card ${on ? 'is-on' : ''}`}
                onMouseEnter={() => setActive(index)}
                onFocus={() => setActive(index)}
                tabIndex={0}
              >
                <Scene on={on} />
                <div className="hw-copy">
                  <span>{step.number}</span>
                  <h3>{step.title}</h3>
                  <p>{step.text}</p>
                </div>
              </article>
            )
          })}
        </div>
      </div>
    </section>
  )
}
