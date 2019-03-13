from autofit import conf
from autofit.tools import path_util
from autolens.data import ccd
from autolens.data.array.util import array_util
from autolens.data.plotters import ccd_plotters

import os

# Welcome to the pipeline runner. This tool allows you to load strong lens data, and pass it to pipelines for a
# PyAutoLens analysis. To show you around, we'll load up some example data and run it through some of the example
# pipelines that come distributed with PyAutoLens.

# The runner is supplied as both this Python script and a Juypter notebook. Its up to you which you use - I personally
# prefer the python script as provided you keep it relatively small, its quick and easy to comment out different lens
# names and pipelines to perform different analyses. However, notebooks are a tidier way to manage visualization - so
# feel free to use notebooks. Or, use both for a bit, and decide your favourite!

# The pipeline runner is fairly self explanatory. Make sure to checkout the pipelines in the
#  workspace/pipelines/examples/ folder - they come with detailed descriptions of what they do. I hope that you'll
# expand on them for your own personal scientific needs

# Setup the path to the workspace, using a relative directory name.
workspace_path = '{}/../'.format(os.path.dirname(os.path.realpath(__file__)))

# Use this path to explicitly set the config path and output path.
conf.instance = conf.Config(config_path=workspace_path + 'config', output_path=workspace_path + 'output')

# It is convenient to specify the data type and data name as a string, so that if the pipeline is applied to multiple
# images we don't have to change all of the path entries in the load_ccd_data_from_fits function below.

data_type = 'example'
data_name = 'lens_light_and_x1_source' # Example simulated image with lens light emission and a source galaxy.
pixel_scale = 0.1

# data_name = 'slacs1430+4105' # Example HST imaging of the SLACS strong lens slacs1430+4150.
# pixel_scale = 0.03

# Create the path where the data will be loaded from, which in this case is
# '/workspace/data/example/lens_light_and_x1_source/'
data_path = path_util.make_and_return_path_from_path_and_folder_names(path=workspace_path,
                                                                      folder_names=['data', data_type, data_name])

ccd_data = ccd.load_ccd_data_from_fits(image_path=data_path + 'image.fits',
                                       psf_path=data_path + 'psf.fits',
                                       noise_map_path=data_path + 'noise_map.fits',
                                       pixel_scale=pixel_scale)

ccd_plotters.plot_ccd_subplot(ccd_data=ccd_data)

# Running a pipeline is easy, we simply import it from the pipelines folder and pass the lens data to its run function.
# Below, we'll' use a 3 phase example pipeline to fit the data with a parametric lens light, mass and source light
# profile. Checkout 'workspace/pipelines/examples/lens_light_and_x1_source_parametric.py' for a full description of
# the pipeline.

# The phase folders input determines the output directory structure of the pipeline, for example the input below makes
# the directory structure:
# 'autolens_workspace/output/phase_folder_1/phase_folder_2/pipeline_name/' or
# 'autolens_workspace/output/example/lens_light_and_x1_source/lens_light_and_x1_source_parametric/'

# For large samples of images, we can therefore easily group lenses that are from the same sample or modeled using the
# same pipeline.

from workspace.pipelines.examples import lens_light_and_x1_source_parametric
pipeline = lens_light_and_x1_source_parametric.make_pipeline(phase_folders=[data_type, data_name])
pipeline.run(data=ccd_data)

# Another pipeline in the examples folder uses 5 phases to ultimately reconstruct the source galaxy on an adaptive
# pixel-grid. To run this pipeline on our data, simply comment out / delete the lines above (lines 47-51) which run
# the parametric souorce pipeline, and uncomment the lines below.

# from workspace.pipelines.examples import lens_light_and_x1_source_parametric

# pipeline = lens_light_and_x1_source_parametric.make_pipeline(phase_folders=[data_type, data_name])

# pipeline.run(data=ccd_data)

# And there we have it, the pipeline runner. For me personally, I find it easiest too manage my lens models by having
# multiple pipeline runners as Python, with each dedicated to a specific set of pipelines and lenses. This makes it
# easier to set off multiple pipelines at the same time, whilst keeping a good sense of what their purpose is.

# You experiment with different runners to figure out the workflow that works best for you - you may well prefer using
# a Juypter notebook to run pipelines, so make sure to checkout the notebook pipeline runner also in this folder.