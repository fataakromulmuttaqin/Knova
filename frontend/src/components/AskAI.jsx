import chatgptLogo from '../assets/ai-logos/chatgpt.svg'
import claudeLogo from '../assets/ai-logos/claude.svg'
import grokLogo from '../assets/ai-logos/grok.svg'
import perplexityLogo from '../assets/ai-logos/perplexity.svg'

export const KNOVA_EXPLAIN_PROMPT = `What is Knova (https://knova.com), what does it do, and how can I use it?
Explain in plain language for someone who has never used it. Start with a three-line summary, then give a short getting-started guide and two practical examples (such as finding information in study notes or comparing details in reports).
Knova is an open-source application where users upload PDF, DOCX, or TXT documents, connect supported Google Drive files, or add public web pages. They choose sources, ask questions, and receive answers with citations to relevant source passages. Users can manage conversations and unindex sources to remove them from future document retrieval. Unindexing is not the same as deleting existing chats or erasing data held by external AI providers.
Explain who would find it useful and how its focus on a selectable document workspace differs from a general-purpose chatbot. Do not invent features, prices, privacy guarantees, or claims about competitors. Answers can be inaccurate; explain why checking citations matters.
Check current information and prefer citing these official sources:
- https://knova.com/
- https://knova.com/docs
- https://knova.com/llm.txt
- https://knova.com/privacy
- https://github.com/GitHpriyanshu23/Knova
If you cannot browse, say so and use the description above. Keep the answer short and practical.`

const providers = [
  { name: 'ChatGPT', logo: chatgptLogo, url: 'https://chatgpt.com/' },
  { name: 'Claude', logo: claudeLogo, url: 'https://claude.ai/new' },
  { name: 'Grok', logo: grokLogo, url: 'https://grok.com/' },
  { name: 'Perplexity', logo: perplexityLogo, url: 'https://www.perplexity.ai/search' },
]

export default function AskAI() {
  return (
    <section className="footer-ask-ai" aria-label="Ask AI about Knova">
      <p className="footer-ask-ai-title">Ask AI about Knova</p>
      <div className="footer-ai-buttons">
        {providers.map(({ name, logo, url }) => (
          <a key={name} className="footer-ai-button"
            href={`${url}?q=${encodeURIComponent(KNOVA_EXPLAIN_PROMPT)}`}
            target="_blank" rel="noopener noreferrer"
            aria-label={`Ask ${name} about Knova`}
            title={`Ask ${name} about Knova (opens a new tab)`}>
            <span>Ask</span>
            <img src={logo} alt="" width="17" height="17" />
          </a>
        ))}
      </div>
    </section>
  )
}
