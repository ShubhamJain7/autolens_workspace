from autofit.tools import path_util
from autofit.optimize import non_linear as nl
from autofit.mapper import prior
from autolens.model.galaxy import galaxy_model as gm
from autolens.pipeline import phase as ph
from autolens.pipeline import pipeline
from autolens.pipeline import tagging as tag
from autolens.model.profiles import light_profiles as lp
from autolens.model.profiles import mass_profiles as mp

import os

# In this pipeline, we'll perform an analysis which fits an image with  no lens light, and a source galaxy using a
# parametric light profile, using a power-law mass profile. The pipeline follows on from the initializer pipeline
# ''pipelines/no_lens_light/initializers/lens_sie_shear_source_sersic_from_init.py'.

# The pipeline is one phase, as follows:

# Phase 1:

# Description: Initializes the lens mass model and source light profile.
# Lens Mass: EllipitcalPowerLaw + ExternalShear
# Source Light: EllipticalSersic
# Previous Pipelines: no_lens_light/initializers/lens_sie_shear_source_sersic_from_init.py
# Prior Passing: None
# Notes: Uses an interpolation pixel scale for fast power-law deflection angle calculations.

def make_pipeline(phase_folders=None, phase_tagging=True, sub_grid_size=2, bin_up_factor=None, positions_threshold=None,
                  inner_mask_radii=None, interp_pixel_scale=0.05):

    pipeline_name = 'pipeline_power_law_lens_power_law_shear_source_sersic'

    # This function uses the phase folders and pipeline name to set up the output directory structure,
    # e.g. 'autolens_workspace/output/phase_folder_1/phase_folder_2/pipeline_name/phase_name/'

    phase_folders = path_util.phase_folders_from_phase_folders_and_pipeline_name(phase_folders=phase_folders,
                                                                                pipeline_name=pipeline_name)

    ### PHASE 1 ###

    # In phase 1, we will fit the lens galaxy's mass and one source galaxy, where we:

    # 1) Set our priors on the lens galaxy mass using the EllipticalIsothermal fit of the previous pipeline, and
    #    source galaxy of the previous pipeline.

    class LensSourcePhase(ph.LensSourcePlanePhase):

        def pass_priors(self, results):

            einstein_radius_mean = results.from_phase('phase_1_lens_sie_shear_source_sersic').constant.lens.mass.einstein_radius

            self.lens_galaxies.lens.mass.centre = results.from_phase('phase_1_lens_sie_shear_source_sersic').variable.lens.mass.centre
            self.lens_galaxies.lens.mass.axis_ratio = results.from_phase('phase_1_lens_sie_shear_source_sersic').variable.lens.mass.axis_ratio
            self.lens_galaxies.lens.mass.phi = results.from_phase('phase_1_lens_sie_shear_source_sersic').variable.lens.mass.phi
            self.lens_galaxies.lens.mass.einstein_radius = prior.GaussianPrior(mean=einstein_radius_mean, sigma=0.3)

            self.lens_galaxies.lens.mass.shear = results.from_phase('phase_1_lens_sie_shear_source_sersic').variable.lens.shear

            centre_mean = results.from_phase('phase_1_lens_sie_shear_source_sersic').constant.source.light.centre
            effective_radius_mean = results.from_phase('phase_1_lens_sie_shear_source_sersic').constant.source.light.effective_radius
            sersic_index_mean = results.from_phase('phase_1_lens_sie_shear_source_sersic').constant.source.light.sersic_index

            self.source_galaxies.source.light.centre.centre_0 = prior.GaussianPrior(mean=centre_mean[0], sigma=0.3)
            self.source_galaxies.source.light.centre.centre_1 = prior.GaussianPrior(mean=centre_mean[1], sigma=0.3)
            self.source_galaxies.source.light.intensity = results.from_phase('phase_1_lens_sie_shear_source_sersic').variable.source.light.intensity
            self.source_galaxies.source.light.effective_radius = prior.GaussianPrior(mean=effective_radius_mean, sigma=1.0)
            self.source_galaxies.source.light.sersic_index = prior.GaussianPrior(mean=sersic_index_mean, sigma=1.5)
            self.source_galaxies.source.light.axis_ratio = results.from_phase('phase_1_lens_sie_shear_source_sersic').variable.source.light.axis_ratio
            self.source_galaxies.source.light.phi = results.from_phase('phase_1_lens_sie_shear_source_sersic').variable.source.light.phi
            
    phase1 = LensSourcePhase(phase_name='phase_1_lens_power_law_shear_source_sersic', phase_folders=phase_folders,
                             phase_tagging=phase_tagging,
                             lens_galaxies=dict(lens=gm.GalaxyModel(mass=mp.EllipticalPowerLaw,
                                                                    shear=mp.ExternalShear)),
                             source_galaxies=dict(source=gm.GalaxyModel(light=lp.EllipticalSersic)),
                             sub_grid_size=sub_grid_size, bin_up_factor=bin_up_factor,
                             positions_threshold=positions_threshold, inner_mask_radii=inner_mask_radii,
                             interp_pixel_scale=interp_pixel_scale,
                             optimizer_class=nl.MultiNest)

    phase1.optimizer.const_efficiency_mode = True
    phase1.optimizer.n_live_points = 75
    phase1.optimizer.sampling_efficiency = 0.2

    return pipeline.PipelineImaging(pipeline_name, phase1)