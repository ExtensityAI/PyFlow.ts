import { SEOQueryOptimizerService, Symbol } from './generated/seo_extensions';

const sqo = new SEOQueryOptimizerService();
const sym = new Symbol('Give me a car after 2010 to drive');

const result = await sqo.forward(sym, {
    temperature: 0,
    seed: 42
});

console.log(result);

