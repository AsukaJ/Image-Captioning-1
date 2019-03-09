from tensorflow.keras.utils import multi_gpu_model
import numpy as np
import tensorflow as tf


class Multi_Model:

  def __init__(self, keras_model, type):
    self.type = type
    self.keras_model = keras_model

  def predict(self, generator, num_samples, batch_size, verbose):
    # TPU requires a fixed batch size for all batches, therefore the number
    # of examples must be a multiple of the batch size, or else examples
    # will get dropped.
    # So we pad with fake examples which are ignored later on.
    if self.type == 'tpu':
      steps = int(np.ceil(num_samples / batch_size))
      dummy_indices = steps * batch_size - num_samples
      generator = tpu_gen(generator, batch_size, dummy_indices)
      print('Steps: {}'.format(steps))
      print('Padding last batch with {} dummy samples'.format(dummy_indices))
      features = self.keras_model.predict(generator, batch_size, steps=steps, verbose=verbose)
      return features[:num_samples]

    else:
      return self.keras_model.predict(generator, num_samples / batch_size, verbose=verbose)


def tpu_gen(generator, batch_size, dummy_indices):
  dummyImages = np.zeros((dummy_indices, 224, 224, 3), dtype=np.uint8)
  for imgs in generator:
    if imgs.shape[0] == batch_size:
      yield imgs
    else:
      yield np.concatenate((imgs, dummyImages), axis=0)


def get_model(model, type, **kwargs):
    if type == 'single':
        model = Multi_Model(model, 'single')

    elif type == 'multi':
        model = multi_gpu_model(model, gpus=2, cpu_relocation=True)
        model = Multi_Model(model, 'multi')

    elif type == 'tpu':
        model = tf.contrib.tpu.keras_to_tpu_model(
            model,
            strategy=tf.contrib.tpu.TPUDistributionStrategy(
                tf.contrib.cluster_resolver.TPUClusterResolver(
                    kwargs['TPU_WORKER'])))
        model = Multi_Model(model, 'tpu')


    model.keras_model.compile(
        optimizer=tf.keras.optimizers.Adam(lr=0.0001, momentum=0.9),
        loss='categorical_crossentropy',
        metrics=['accuracy'])

    return model
