import React from "react";
import {
  Accordion,
  AccordionItem,
  AccordionTrigger,
  AccordionContent,
} from "@/components/ui/accordion";

export const defaultFAQs = [
  {
    question: "Sumber data apa saja yang bisa saya hubungkan ke KNOVA?",
    answer:
      "Kamu bisa upload file PDF, DOCX, dan TXT, menambahkan halaman HTTP atau HTTPS, serta mengimpor konten PDF, TXT, dan Google Docs yang didukung dari Google Drive. Teks hasil ekstraksi di-chunk lalu disimpan di koleksi Chroma aplikasi untuk retrieval.",
  },
  {
    question: "Bagaimana KNOVA menyitasi sumber dan menekan jawaban tanpa dasar?",
    answer:
      "KNOVA meminta model menjawab dari passage dokumen berperingkat teratas dan mengembalikan kutipan sumber hasil retrieval bersama jawabannya. Tombol sitasi memungkinkan kamu memeriksa bukti tersebut, tetapi klaim penting tetap sebaiknya diverifikasi ke dokumen aslinya.",
  },
  {
    question: "Apa itu hybrid search dan kenapa lebih unggul dari vector search murni?",
    answer:
      "Dense vector embedding unggul pada makna konseptual yang luas, tetapi sering melewatkan istilah teknis persis, ID produk, atau angka finansial. KNOVA memasangkan dense vector retrieval dengan BM25 sparse lexical search, lalu menggabungkannya memakai Reciprocal Rank Fusion (RRF) dan cross-encoder reranking agar presisinya maksimal.",
  },
  {
    question: "Apakah memori chat dan data dokumen terisolasi per sesi?",
    answer:
      "Ya. Thread, pesan, memori, sumber, dan retrieval dibatasi pada user yang sudah login. Konteks multi-turn tetap berada di dalam thread yang dipilih, dan kamu bisa membersihkan atau menghapus percakapan kapan saja.",
  },
  {
    question: "Di mana data disimpan dan diproses?",
    answer:
      "Vector dokumen dan metadata aplikasi disimpan oleh backend Chroma dan SQL yang dikonfigurasi. Pembuatan jawaban memakai model provider yang dikonfigurasi, jadi konteks hasil retrieval bisa dikirim ke provider tersebut; aplikasi ini secara default bukan deployment air-gapped.",
  },
  {
    question: "Bagaimana KNOVA menangani struktur dokumen?",
    answer:
      "KNOVA mengekstrak teks dari dokumen PDF, DOCX, dan TXT serta mempertahankan metadata halaman selama parser menyediakannya. PDF hasil scan perlu OCR sebelum diunggah, dan ingestion spreadsheet belum didukung saat ini.",
  },
  {
    question: "Bagaimana kualitas retrieval diukur dan dievaluasi?",
    answer:
      "KNOVA menyediakan perintah evaluasi RAGAS untuk Faithfulness, Answer Relevancy, dan Context Precision. Perintah itu bisa menegakkan ambang batas minimum terhadap dataset uji domain yang berversi sebelum rilis.",
  },
];

export default function FrequentlyAskedQuestions({
  badge = "FAQ",
  title = "Pertanyaan umum, jawaban jelas.",
  description = "Semua yang perlu kamu tahu soal presisi retrieval, privasi data, dan arsitektur.",
  data = defaultFAQs,
  className = "",
  supportEmail = "",
}) {
  return (
    <section
      id="faq"
      className={`faq-root-section ${className}`.trim()}
      data-nav-theme="light"
      aria-label="Pertanyaan yang Sering Diajukan"
    >
      <div className="faq-container">
        <div className="faq-grid">
          
          {/* Left Column: Badge, Headline & Subtitle */}
          <div className="faq-left-col">
            {badge && <div className="faq-badge">{badge}</div>}

            <h2 className="faq-headline">
              {title === "Pertanyaan umum, jawaban jelas." ? (
                <>
                  Pertanyaan umum,<br />jawaban jelas.
                </>
              ) : (
                title
              )}
            </h2>

            <p className="faq-desc">
              {description}
              {supportEmail && (
                <>
                  <br />
                  <a
                    href={`mailto:${supportEmail}`}
                    className="faq-email-link"
                  >
                    {supportEmail}
                  </a>
                </>
              )}
            </p>
          </div>

          {/* Right Column: Accordion list */}
          <div className="faq-right-col">
            <Accordion type="single" collapsible defaultValue="item-0">
              {data.map((item, index) => (
                <AccordionItem key={`faq-${index}`} value={`item-${index}`}>
                  <AccordionTrigger>{item.question}</AccordionTrigger>
                  <AccordionContent>{item.answer}</AccordionContent>
                </AccordionItem>
              ))}
            </Accordion>
          </div>

        </div>
      </div>
    </section>
  );
}
