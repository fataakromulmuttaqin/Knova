import { useState } from 'react'
import { AnimatePresence, motion, useReducedMotion } from 'motion/react'
import { BookOpen, Check, Cloud, FileSearch, Files, Terminal } from 'lucide-react'
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from '../ui/accordion.jsx'

const workflows = [
  {
    id: 'policies',
    number: '01',
    title: 'Kebijakan dan handbook',
    icon: FileSearch,
    prompt: '“Apa yang berubah di kebijakan cuti kami, dan di mana tertulisnya?”',
    description: 'Ambil passage kebijakan dari konten PDF, DOCX, TXT, dan website yang sudah di-index, lalu periksa kutipan di balik jawabannya.',
    outcome: ['Hybrid semantic dan keyword retrieval', 'Sitasi inline ke passage hasil retrieval', 'Teks sumber tersedia untuk verifikasi'],
    formats: ['PDF', 'DOCX', 'TXT', 'Halaman web'],
  },
  {
    id: 'engineering',
    number: '02',
    title: 'Dokumentasi engineering',
    icon: Terminal,
    prompt: '“Check apa saja yang diwajibkan runbook deployment?”',
    description: 'Cari catatan arsitektur, runbook, panduan rilis, dan dokumen teknis berbasis teks lain dalam satu workspace yang ter-index.',
    outcome: ['CrossEncoder reranking', 'Follow-up yang sadar konteks percakapan', 'Sumber dokumen yang bisa dipilih'],
    formats: ['Runbook', 'ADR', 'Panduan', 'Dokumen statis'],
  },
  {
    id: 'drive',
    number: '03',
    title: 'Pengetahuan di Google Drive',
    icon: Cloud,
    prompt: '“Ringkas materi onboarding di file Drive yang dipilih.”',
    description: 'Hubungkan Google Drive dengan akses read-only dan sinkronkan file yang didukung secara manual ke index privat khusus milik user.',
    outcome: ['Koneksi Google Drive read-only', 'Pilih file mana yang disinkronkan', 'Link Drive di sitasi sumber'],
    formats: ['Google Docs', 'Drive PDFs', 'Drive TXT'],
  },
  {
    id: 'research',
    number: '04',
    title: 'Riset multi-dokumen',
    icon: Files,
    prompt: '“Bandingkan bagaimana dokumen-dokumen ini mendefinisikan kebutuhan yang sama.”',
    description: 'Ajukan pertanyaan di seluruh koleksi yang ter-index dan tinjau passage terkuat hasil retrieval sebelum mempercayai sintesisnya.',
    outcome: ['Beberapa dokumen ter-index', 'Retrieval dengan sumber beragam', 'Riwayat percakapan yang tersimpan'],
    formats: ['Laporan', 'Catatan', 'Referensi', 'Sumber web'],
  },
]

function WorkflowDetail({ workflow }) {
  const Icon = workflow.icon
  return (
    <div className="workflow-detail-inner">
      <div className="workflow-detail-icon"><Icon size={21} /></div>
      <p className="workflow-prompt">{workflow.prompt}</p>
      <h3>{workflow.title}</h3>
      <p className="workflow-description">{workflow.description}</p>
      <div className="workflow-proof-list">
        {workflow.outcome.map((item) => <span key={item}><Check size={14} /> {item}</span>)}
      </div>
      <div className="workflow-formats">{workflow.formats.map((item) => <span key={item}>{item}</span>)}</div>
    </div>
  )
}

export default function UseCasesSection() {
  const [activeId, setActiveId] = useState(workflows[0].id)
  const reduceMotion = useReducedMotion()
  const active = workflows.find((item) => item.id === activeId) || workflows[0]

  return (
    <section className="use-cases-section" data-nav-theme="dark" aria-labelledby="workflows-title">
      <div className="use-cases-inner">
        <div className="section-head-dark editorial-workflow-head">
          <span className="section-badge-dark"><BookOpen size={12} /> BEKERJA DENGAN PENGETAHUANMU</span>
          <h2 id="workflows-title">Satu alur retrieval.<br />Beragam jenis pertanyaan.</h2>
          <p>Pakai Knova saat dokumen pendukung sama pentingnya dengan jawaban yang dihasilkan.</p>
        </div>

        <div className="workflow-desktop">
          <div className="workflow-tabs" role="tablist" aria-label="Alur kerja dokumen">
            {workflows.map((workflow) => {
              const Icon = workflow.icon
              const selected = workflow.id === active.id
              return (
                <button key={workflow.id} type="button" role="tab" aria-selected={selected} aria-controls={`workflow-panel-${workflow.id}`} className={selected ? 'active' : ''} onClick={() => setActiveId(workflow.id)}>
                  <span>{workflow.number}</span><Icon size={18} /><strong>{workflow.title}</strong>
                </button>
              )
            })}
          </div>
          <div className="workflow-panel" role="tabpanel" id={`workflow-panel-${active.id}`}>
            <AnimatePresence mode="wait">
              <motion.div key={active.id} initial={reduceMotion ? false : { opacity: 0, x: 18 }} animate={{ opacity: 1, x: 0 }} exit={reduceMotion ? undefined : { opacity: 0, x: -12 }} transition={{ duration: .25 }}>
                <WorkflowDetail workflow={active} />
              </motion.div>
            </AnimatePresence>
          </div>
        </div>

        <Accordion type="single" defaultValue={workflows[0].id} className="workflow-mobile">
          {workflows.map((workflow) => (
            <AccordionItem key={workflow.id} value={workflow.id} className="workflow-mobile-item">
              <AccordionTrigger className="workflow-mobile-trigger"><span>{workflow.number}</span>{workflow.title}</AccordionTrigger>
              <AccordionContent className="workflow-mobile-content"><WorkflowDetail workflow={workflow} /></AccordionContent>
            </AccordionItem>
          ))}
        </Accordion>
      </div>
    </section>
  )
}
