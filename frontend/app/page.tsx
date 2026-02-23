import Link from 'next/link';

export default function Home() {
  return (
    <main className="min-h-screen bg-[#fdfaf6] text-[#2d1b1b] flex flex-col items-center justify-center p-6 relative overflow-hidden font-sans">

      {/* Background Subtle Texture/Decor */}
      <div className="absolute inset-0 opacity-[0.03] pointer-events-none" style={{ backgroundImage: 'radial-gradient(#2d1b1b 0.5px, transparent 0.5px)', backgroundSize: '24px 24px' }} />

      <div className="absolute -top-24 -left-24 w-96 h-96 bg-[#5c1414]/5 rounded-full blur-[120px] pointer-events-none" />
      <div className="absolute -bottom-24 -right-24 w-96 h-96 bg-[#c5a059]/10 rounded-full blur-[120px] pointer-events-none" />

      <div className="z-10 text-center space-y-12 max-w-4xl animate-fade-in">
        <div className="space-y-4">
          <p className="text-xs font-medium tracking-[0.4em] text-[#c5a059] uppercase">Experiencia Gastronómica</p>
          <h1 className="text-7xl md:text-9xl font-serif tracking-tight text-[#5c1414]">
            Sabor Divino
          </h1>
          <div className="w-24 h-px bg-[#c5a059] mx-auto opacity-50" />
        </div>

        <p className="text-xl md:text-2xl text-[#2d1b1b]/70 font-light max-w-2xl mx-auto leading-relaxed italic font-serif">
          "Donde la herencia mediterránea se encuentra con la pasión de la tierra chilena."
        </p>

        <div className="flex flex-col sm:flex-row gap-8 justify-center items-center pt-8">
          <Link href="/chat" className="group relative w-72 h-16 flex items-center justify-center overflow-hidden border border-[#5c1414] transition-all hover:bg-[#5c1414]">
            <span className="z-10 relative text-[#5c1414] group-hover:text-[#fdfaf6] font-medium tracking-[0.2em] uppercase text-sm transition-colors">
              Reservar una Mesa
            </span>
            <div className="absolute inset-x-0 bottom-0 h-0 bg-[#5c1414] transition-all group-hover:h-full" />
          </Link>

          <Link href="/admin" className="text-[#2d1b1b]/40 hover:text-[#c5a059] transition-colors text-xs tracking-widest uppercase font-medium">
            Portal Administrativo
          </Link>
        </div>
      </div>

      {/* Footer Decoration */}
      <div className="absolute bottom-8 text-[10px] tracking-[0.5em] text-[#2d1b1b]/20 uppercase font-light">
        Santiago | Chile | 2026
      </div>
    </main>
  );
}
