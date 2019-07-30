import autofit as af
from autolens.model.galaxy import galaxy_model as gm
from autolens.pipeline.phase import phase_imaging
from autolens.pipeline import pipeline
from autolens.pipeline import pipeline_tagging
from autolens.model.profiles import mass_profiles as mp
from autolens.model.inversion import pixelizations as pix
from autolens.model.inversion import regularization as reg

import os

# In this pipeline, we'll perform a subhalo analysis which determines the sensitivity map of a strong lens and
# then attempts to detection subhalos by putting subhalos at fixed intevals on a 2D (y,x) grid. The source uses an
# inversion. The pipeline is as follows:

# Phase 1:

# Description: Perform the subhalo detection analysis.
# Lens Mass: EllipitcalPowerLaw + ExternalShear
# Source Light: VoronoiBrightnessImage + Constant
# Subhalo: SphericalTruncatedNFWChallenge
# Previous Pipelines: initialize/lens_sie_source_inversion_from_pipeline.py
# Prior Passing: Lens Mass constant from previous pipeline, source light variable from previous pipeline.
# Notes: Priors on subhalo are tuned to give realistic masses (10^6 - 10^10) and concentrations (6-24)

# Phase 2:

# Description: Refine the best-fit detected subhalo from the previous phase, by varying also the lens mass model.
# Lens Mass: EllipitcalPowerLaw + ExternalShear
# Source Light: VoronoiBrightnessImage + Constant
# Subhalo: SphericalTruncatedNFWChallenge
# Previous Pipelines: initialize/lens_sie_source_inversion_from_pipeline.py
# Prior Passing: Lens Mass variable from previous pipeline, source light and subhalo mass variable from phase 2.
# Notes: None


def make_pipeline(
    pipeline_settings,
    phase_folders=None,
    tag_phases=True,
    redshift_lens=0.5,
    redshift_source=1.0,
    sub_grid_size=2,
    bin_up_factor=None,
    positions_threshold=None,
    inner_mask_radii=None,
    interp_pixel_scale=0.05,
    use_inversion_border=True,
    inversion_pixel_limit=None,
    cluster_pixel_scale=0.1,
):

    ### SETUP PIPELINE AND PHASE NAMES, TAGS AND PATHS ###

    # We setup the pipeline name using the tagging module. In this case, the pipeline name is not given a tag and
    # will be the string specified below However, its good practise to use the 'tag.' function below, incase
    # a pipeline does use customized tag names.

    pipeline_name = "pipeline_subhalo__lens_pl_subhalo_source_inversion"

    pipeline_name = pipeline_tagging.pipeline_name_from_name_and_settings(
        pipeline_name=pipeline_name,
        include_shear=pipeline_settings.include_shear,
        pixelization=pipeline_settings.pixelization,
        regularization=pipeline_settings.regularization,
    )

    phase_folders.append(pipeline_name)

    ### Phase 1 ###

    # In phase 1, we attempt to detect subhalos, by performing a NxN grid search of MultiNest searches, where:

    # 1) The lens model and source-pixelization parameters are held fixed to the best-fit values from phase 2.
    # 2) Each grid search varies the subhalo (y,x) coordinates and mass as free parameters.
    # 3) The priors on these (y,x) coordinates are UniformPriors, with limits corresponding to the grid-cells.

    class GridPhase(af.as_grid_search(phase_imaging.PhaseImaging)):
        @property
        def grid_priors(self):
            return [
                self.variable.galaxies.subhalo.mass.centre_0,
                self.variable.galaxies.subhalo.mass.centre_1,
            ]

        def pass_priors(self, results):

            ### Lens Mass, PL -> PL, Shear -> Shear ###

            self.galaxies.lens = results.from_phase(
                "phase_1_lens_pl_source_inversion"
            ).constant.galaxies.lens

            ### Lens Subhalo, Adjust priors to physical masses (10^6 - 10^10) and concentrations (6-24)

            self.galaxies.subhalo.mass.kappa_s = af.UniformPrior(
                lower_limit=0.0005, upper_limit=0.2
            )
            self.galaxies.subhalo.mass.scale_radius = af.UniformPrior(
                lower_limit=0.001, upper_limit=1.0
            )
            self.galaxies.subhalo.mass.centre_0 = af.UniformPrior(
                lower_limit=-2.0, upper_limit=2.0
            )
            self.galaxies.subhalo.mass.centre_1 = af.UniformPrior(
                lower_limit=-2.0, upper_limit=2.0
            )

            ### Source Inversion, Inv -> Inv ###

            self.galaxies.source = results.from_phase(
                "phase_1_lens_pl_source_inversion"
            ).hyper_combined.constant.galaxies.source

            ## Set all hyper-galaxies if feature is turned on ##

            if pipeline_settings.hyper_galaxies:

                self.galaxies.source.hyper_galaxy = (
                    results.last.hyper_combined.constant.galaxies.source.hyper_galaxy
                )

            if pipeline_settings.hyper_background_sky:

                self.hyper_image_sky = (
                    results.last.hyper_combined.constant.hyper_image_sky
                )

            if pipeline_settings.hyper_background_noise:

                self.hyper_noise_background = (
                    results.last.hyper_combined.constant.hyper_noise_background
                )

    phase1 = GridPhase(
        phase_name="phase_1_subhalo_search",
        phase_folders=phase_folders,
        tag_phases=tag_phases,
        galaxies=dict(
            lens=gm.GalaxyModel(
                redshift=redshift_lens,
                mass=mp.EllipticalPowerLaw,
                shear=mp.ExternalShear,
            ),
            subhalo=gm.GalaxyModel(
                redshift=redshift_lens, mass=mp.SphericalTruncatedNFWChallenge
            ),
            source=gm.GalaxyModel(
                redshift=redshift_source,
                pixelization=pipeline_settings.pixelization,
                regularization=pipeline_settings.regularization,
            ),
        ),
        sub_grid_size=sub_grid_size,
        bin_up_factor=bin_up_factor,
        positions_threshold=positions_threshold,
        inner_mask_radii=inner_mask_radii,
        interp_pixel_scale=interp_pixel_scale,
        use_inversion_border=use_inversion_border,
        inversion_pixel_limit=inversion_pixel_limit,
        cluster_pixel_scale=cluster_pixel_scale,
        optimizer_class=af.MultiNest,
        number_of_steps=4,
    )

    phase1.optimizer.const_efficiency_mode = True
    phase1.optimizer.n_live_points = 20
    phase1.optimizer.sampling_efficiency = 0.3

    class SubhaloPhase(phase_imaging.PhaseImaging):
        def pass_priors(self, results):

            ### Lens Mass, PL -> PL, Shear -> Shear ###

            self.galaxies.lens = results.from_phase(
                "phase_1_lens_pl_source_inversion"
            ).variable.galaxies.lens

            ### Subhalo, TruncatedNFW -> TruncatedNFW ###

            self.galaxies.subhalo.mass.centre = (
                results.from_phase("phase_1_subhalo_search")
                .best_result.variable_absolute(a=0.3)
                .galaxies.subhalo.mass.centre
            )

            self.galaxies.subhalo.mass.kappa_s = (
                results.from_phase("phase_1_subhalo_search")
                .best_result.variable_relative(r=0.5)
                .galaxies.subhalo.mass.kappa_s
            )

            self.galaxies.subhalo.mass.scale_radius = (
                results.from_phase("phase_1_subhalo_search")
                .best_result.variable_relative(r=0.5)
                .galaxies.subhalo.mass.scale_radius
            )

            ### Source Inversion, Inv -> Inv ###

            self.galaxies.source = results.from_phase(
                "phase_1_lens_pl_source_inversion"
            ).hyper_combined.constant.galaxies.source

            ## Set all hyper-galaxies if feature is turned on ##

            if pipeline_settings.hyper_galaxies:

                self.galaxies.source.hyper_galaxy = results.from_phase(
                    "phase_1_lens_pl_source_inversion"
                ).hyper_combined.constant.galaxies.source.hyper_galaxy

            if pipeline_settings.hyper_background_sky:

                self.hyper_image_sky = results.from_phase(
                    "phase_1_lens_pl_source_inversion"
                ).hyper_combined.constant.hyper_image_sky

            if pipeline_settings.hyper_background_noise:

                self.hyper_noise_background = results.from_phase(
                    "phase_1_lens_pl_source_inversion"
                ).hyper_combined.constant.hyper_noise_background

    phase2 = SubhaloPhase(
        phase_name="phase_2_subhalo_refine",
        phase_folders=phase_folders,
        tag_phases=tag_phases,
        galaxies=dict(
            lens=gm.GalaxyModel(
                redshift=redshift_lens,
                mass=mp.EllipticalPowerLaw,
                shear=mp.ExternalShear,
            ),
            subhalo=gm.GalaxyModel(
                redshift=redshift_lens, mass=mp.SphericalTruncatedNFWChallenge
            ),
            source=gm.GalaxyModel(
                redshift=redshift_source,
                pixelization=pipeline_settings.pixelization,
                regularization=pipeline_settings.regularization,
            ),
        ),
        sub_grid_size=sub_grid_size,
        bin_up_factor=bin_up_factor,
        positions_threshold=positions_threshold,
        inner_mask_radii=inner_mask_radii,
        interp_pixel_scale=interp_pixel_scale,
        use_inversion_border=use_inversion_border,
        inversion_pixel_limit=inversion_pixel_limit,
        cluster_pixel_scale=cluster_pixel_scale,
        optimizer_class=af.MultiNest,
    )

    phase2.optimizer.const_efficiency_mode = True
    phase2.optimizer.n_live_points = 80
    phase2.optimizer.sampling_efficiency = 0.3

    phase2 = phase2.extend_with_multiple_hyper_phases(
        hyper_galaxy=pipeline_settings.hyper_galaxies,
        include_background_sky=pipeline_settings.hyper_background_sky,
        include_background_noise=pipeline_settings.hyper_background_noise,
        inversion=True,
    )

    return pipeline.PipelineImaging(pipeline_name, phase1, phase2, hyper_mode=True)
