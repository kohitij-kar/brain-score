import numpy as np

import brainscore
from brainscore.benchmarks import BenchmarkBase
from brainscore.metrics import Score
from brainscore.metrics.image_level_behavior import I2n
from brainscore.metrics.transformations import apply_aggregate
from brainscore.model_interface import BrainModel
from brainscore.benchmarks.screen import place_on_screen
from brainscore.utils import LazyLoad


class DicarloRajalingham2018I2n(BenchmarkBase):
    def __init__(self):
        self._metric = I2n()
        self._fitting_stimuli = brainscore.get_stimulus_set('dicarlo.objectome.public')
        self._assembly = LazyLoad(lambda: load_assembly('private'))
        self._visual_degrees = 8
        super(DicarloRajalingham2018I2n, self).__init__(
            identifier='dicarlo.Rajalingham2018-i2n', version=2,
            ceiling_func=lambda: self._metric.ceiling(self._assembly),
            parent='behavior',
            paper_link='https://www.biorxiv.org/content/early/2018/02/12/240614')

    def __call__(self, candidate: BrainModel):
        fitting_stimuli = place_on_screen(self._fitting_stimuli, target_visual_degrees=candidate.visual_degrees(),
                                          source_visual_degrees=self._visual_degrees)
        candidate.start_task(BrainModel.Task.probabilities, fitting_stimuli)
        stimulus_set = place_on_screen(self._assembly.stimulus_set, target_visual_degrees=candidate.visual_degrees(),
                                       source_visual_degrees=self._visual_degrees)
        probabilities = candidate.look_at(stimulus_set)
        score = self._metric(probabilities, self._assembly)
        score = self.ceil_score(score, self.ceiling)
        return score

    def ceil_score(self, score, ceiling):
        assert set(score.raw['split'].values) == set(ceiling.raw['split'].values)
        split_scores = []
        for split in ceiling.raw['split'].values:
            split_score = score.raw.sel(split=split)
            split_ceiling = ceiling.raw.sel(split=split)
            ceiled_split_score = split_score / np.sqrt(split_ceiling)
            ceiled_split_score = ceiled_split_score.expand_dims('split')
            ceiled_split_score['split'] = [split]
            split_scores.append(ceiled_split_score)
        split_scores = Score.merge(*split_scores)
        split_scores = apply_aggregate(self._metric.aggregate, split_scores)
        split_scores.attrs[Score.RAW_VALUES_KEY] = score  # this will override raw per-split ceiled scores which is ok
        split_scores.attrs['ceiling'] = ceiling
        return split_scores


def load_assembly(access='private'):
    assembly = brainscore.get_assembly(f'dicarlo.Rajalingham2018.{access}')
    assembly['correct'] = assembly['choice'] == assembly['sample_obj']
    return assembly
