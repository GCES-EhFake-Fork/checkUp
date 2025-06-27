import { useEffect, useState } from "react";
import { Button } from "./components/ui/button";

const API_URL = "http://localhost:8000";

const Home = () => {
	const [portais, setPortais] = useState<string[]>([]);
	const [loading, setLoading] = useState(true);
	const [erro, setErro] = useState("");
	const [portalSelecionado, setPortalSelecionado] = useState<string | null>(
		null,
	);

	useEffect(() => {
		fetch(`${API_URL}/portais`)
			.then((res) => res.json())
			.then(setPortais)
			.catch(() => setErro("Erro ao buscar portais"))
			.finally(() => setLoading(false));
	}, []);

	if (loading) return <div className="p-8">Carregando portais...</div>;
	if (erro) return <div className="p-8 text-red-500">{erro}</div>;

	return (
		<div className="max-w-xl mx-auto p-8">
			<h1 className="text-2xl font-bold mb-4">
				Selecione um portal de notícias
			</h1>
			{!portalSelecionado ? (
				<ul className="space-y-2">
					{portais.map((portal) => (
						<li key={portal}>
							<Button
								className="px-4 py-2 rounded bg-zinc-100 hover:bg-zinc-200 border w-full text-left"
								onClick={() => setPortalSelecionado(portal)}
							>
								{portal}
							</Button>
						</li>
					))}
				</ul>
			) : (
				<div>
					<Button
						className="mb-4 text-sm underline"
						onClick={() => setPortalSelecionado(null)}
					>
						&larr; Trocar portal
					</Button>
					<div className="mb-2 font-semibold">
						Portal selecionado:{" "}
						<span className="text-blue-600">{portalSelecionado}</span>
					</div>
					{/* Aqui entraremos com a barra de busca e resultados */}
					<div className="mt-4">[Barra de busca e resultados aqui]</div>
				</div>
			)}
		</div>
	);
};

export default Home;
