import { Link } from 'react-router-dom'
import brandLogoDark from '../assets/figma-logo-mark-dark.svg'
import AskAI from './AskAI.jsx'

export default function SiteFooter() {
  return (
    <footer className="site-footer">
      <div className="footer-inner">
        <div className="footer-brand">
          <Link to="/" className="footer-logo-link">
            <img src={brandLogoDark} alt="" className="footer-logo-img" />
            <span>KNOVA</span>
          </Link>
          <p className="footer-copyright">© Knova 2026. Seluruh hak dilindungi.</p>
          <AskAI />
        </div>

        <div className="footer-links">
          <div className="footer-col">
            <h4>Produk</h4>
            <Link to="/#capabilities">Fitur</Link>
            <Link to="/login?mode=signin">Asisten Chat</Link>
            <Link to="/login?mode=signup">Mulai</Link>
          </div>
          <div className="footer-col">
            <h4>Sumber Daya</h4>
            <Link to="/docs">Dokumentasi</Link>
            <Link to="/#how-it-works">Cara kerja</Link>
            <Link to="/#faq">FAQ</Link>
          </div>
          <div className="footer-col">
            <h4>Legal</h4>
            <Link to="/privacy">Kebijakan Privasi</Link>
            <Link to="/terms">Ketentuan Layanan</Link>
            <Link to="/cookies">Kebijakan Cookie</Link>
          </div>
          <div className="footer-col">
            <h4>Akun</h4>
            <Link to="/login?mode=signup">Buat akun</Link>
            <Link to="/login?mode=signin">Masuk</Link>
          </div>
        </div>
      </div>
      <div className="footer-watermark" aria-hidden="true">Knova</div>
    </footer>
  )
}
