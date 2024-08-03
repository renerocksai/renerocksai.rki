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

    def get_embeddings_batch(self, batch):
        time_start = time()
        batch_name = f'batch-{time_start}'
        if self.dims is None:
            response = client.embeddings.create(model=self.name, input=batch)
        else:
            response = client.embeddings.create(model=self.name,
                                                input=batch,
                                                dimensions=self.dims)
        time_end = time()
        embeddings = [data.embedding for data in response.data]
        usage = response.usage
        stats = EmbeddingStats(prompt_tokens=usage.prompt_tokens,
                               time=time_end - time_start)
        self.stats.add(stats)
        self.sentence_stats[batch_name] = stats
        return embeddings, stats

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
    def __init__(self, name, model=DEFAULT_MODEL):
        self.model = Model(name=model)
        self.cache_file = f'{name}_{self.model.name}_{self.model.dims}.pkl'
        self.values = {}
        self.load_cache()

    def load_cache(self):
        self.values = {}
        if os.path.exists(self.cache_file):
            print('Loading embeddings cache...')
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
            if auto_save:
                self.save_cache()
        else:
            embedding = self.values[sentence]
        return embedding

    def get_batch(self, sentence_batch, auto_save=False):
        # find uncached sentences
        new_batch = [s for s in sentence_batch if s not in self.values]

        if new_batch:
            # we need to process some of the batch
            embeddings, stats = self.model.get_embeddings_batch(new_batch)
            for embedding, sentence in zip(embeddings, new_batch):
                self.values[sentence] = embedding
            if auto_save:
                self.save_cache()
        embeddings = []
        for sentence in sentence_batch:
            embeddings.append(self.values[sentence])
        return embeddings
