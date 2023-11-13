from PIL import Image

from modules import devices
from modules.processing import StableDiffusionProcessingImg2Img

from sd_bmab import masking
from sd_bmab.base.context import Context
from sd_bmab.base.processorbase import ProcessorBase
from sd_bmab.detectors import UltralyticsPersonDetector8n


class Img2imgMasking(ProcessorBase):
	def __init__(self) -> None:
		super().__init__()

	def preprocess(self, context: Context, image: Image):
		self.enabled = context.args['detect_enabled']
		self.prompt = context.args['masking_prompt']
		self.input_image = context.args['input_image']
		return isinstance(context.sdprocessing, StableDiffusionProcessingImg2Img) and self.enabled

	def sam(self, context, prompt, input_image):
		detector = UltralyticsPersonDetector8n()
		boxes, logits = detector.predict(context, input_image)
		sam = masking.get_mask_generator()
		mask = sam.predict(input_image, boxes)
		return mask

	def process(self, context: Context, image: Image):
		if context.sdprocessing.image_mask is not None:
			context.sdprocessing.image_mask = self.sam(self.prompt, context.sdprocessing.init_images[0])
			context.script.extra_image.append(context.sdprocessing.image_mask)
		if context.sdprocessing.image_mask is None and self.input_image is not None:
			mask = self.sam(context, self.prompt, context.sdprocessing.init_images[0])
			newpil = Image.new('RGB', context.sdprocessing.init_images[0].size)
			newdata = [bdata if mdata == 0 else ndata for mdata, ndata, bdata in
			           zip(mask.getdata(), context.sdprocessing.init_images[0].getdata(), self.input_image.getdata())]
			newpil.putdata(newdata)
			context.script.extra_image.append(newpil)
			return newpil
		return image

	def postprocess(self, context: Context, image: Image):
		devices.torch_gc()
