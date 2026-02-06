export default function TrainingPage() {
  return (
    <div className="p-6">
      <h1 className="text-[22px] font-bold text-wybe-text-bright mb-5">
        Training
      </h1>
      <div className="bg-wybe-bg-secondary border border-wybe-border rounded-xl p-8 text-center">
        <p className="text-wybe-text-muted mb-4">
          Migration in progress — training management coming in Phase 3.
        </p>
        <a
          href="/"
          className="text-sm text-wybe-accent hover:text-wybe-accent-hover transition-colors"
          target="_blank"
          rel="noopener noreferrer"
        >
          Use Gradio UI on port 7860 &rarr;
        </a>
      </div>
    </div>
  );
}
