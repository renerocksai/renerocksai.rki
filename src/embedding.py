from dataclasses import dataclass
import os
from time import time
from collections import OrderedDict
from openai import OpenAI
import pickle

DEFAULT_MODEL ='text-embedding-3-large'
DEFAULT_DIMS = 3072

client = OpenAI(api_key=os.environ['OPENAI_RKI_KEY'])

@dataclass
class EmbeddingStats:
    prompt_tokens: int = 0
    time: float = 0.0
    n: int = 0

    def add(self, other):
        self.prompt_tokens += other.prompt_tokens
        self.time += other.time
        self.n += other.n

    def __str__(self):
        return f'p={self.prompt_tokens} d={self.time:.3f} n={self.n}'


class Model:
    def __init__(self, name=DEFAULT_MODEL, dims=None):
        self.name = name
        self.dims = dims
        self.check_dims()
        self.stats = EmbeddingStats()
        self.sentence_stats : dict[str, EmbeddingStats] = OrderedDict()
        self.already_saved_stat_sentences = set()

    def check_dims(self):
        model_max_dims = {
            'text-embedding-3-large': 3072,
            'text-embedding-3-small': 1536,
            'text-embedding-ada-002': 1536,
            }
        max_dims = model_max_dims.get(self.name, None)
        if max_dims is None:
            raise RuntimeError(f'Model {self.name} does not exist')
        if self.dims is None:
            self.dims = max_dims
        if self.dims > max_dims:
            raise ValueError(f'Model {self.name} can handle only {max_dims} dims. Requested: {self.dims}')
        return

    def get_embeddings(self, sentence):
        time_start = time()
        if self.dims is None:
            response = client.embeddings.create(model=self.name, input=sentence)
        else:
            response = client.embeddings.create(model=self.name,
                                                input=sentence,
                                                dimensions=self.dims)
        time_end = time()
        embedding = response.data[0].embedding
        usage = response.usage
        stats = EmbeddingStats(prompt_tokens=usage.prompt_tokens,
                               time=time_end - time_start)
        self.stats.add(stats)
        self.sentence_stats[sentence] = stats
        return embedding, stats

    def save_stats(self):
        stats_filn = f'modelstats_{self.name}_{self.dims}.csv'
        if not os.path.exists(stats_filn):
            f = open(stats_filn, 'wt')
            f.write('num_tokens;time;sentence\n')
        else:
            f = open(stats_filn, 'at')
        for sentence, stats in self.sentence_stats.items():
            if sentence not in self.already_saved_stat_sentences:
                f.write(f'{stats.prompt_tokens};{stats.time};{sentence}\n')
                self.already_saved_stat_sentences.add(sentence)
        f.flush()
        f.close()


class EmbeddingCache:
    def __init__(self, model=DEFAULT_MODEL):
        self.model = Model(name=model)
        self.cache_file = f'__embedding_cache_{self.model.name}_{self.model.dims}.pkl'
        self.values = {}
        self.load_cache()

    def load_cache(self):
        self.values = {}
        if os.path.exists(self.cache_file):
            with open(self.cache_file, 'rb') as f:
                self.values = pickle.load(f)
        return

    # Save embeddings to chache
    def save_cache(self):
        with open(self.cache_file, 'wb') as f:
            pickle.dump(self.values, f)
        self.model.save_stats()

    def get(self, sentence, auto_save=False):
        if sentence not in self.values:
            embedding, stats = self.model.get_embeddings(sentence)
            self.values[sentence] = embedding
        else:
            embedding = self.values[sentence]
        if auto_save:
            self.save_cache()
        return embedding
