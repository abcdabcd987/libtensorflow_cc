# pip install tensorflow==1.13.2 Pillow

import tensorflow as tf
from tensorflow.keras.datasets import mnist
from PIL import Image


def main():
    (x_train_u8, y_train), (x_test_u8, y_test) = mnist.load_data()
    x_train, x_test = x_train_u8 / 255.0, x_test_u8 / 255.0

    img_idx = 1234
    im = Image.fromarray(x_test_u8[img_idx])
    im.save(f"xtest_{img_idx}.png")
    with open(f"xtest_{img_idx}.txt", "w") as f:
        for xs in x_test_u8[img_idx]:
            for x in xs:
                f.write(f'{x:4d}')
            f.write('\n')

    sess = tf.keras.backend.get_session()
    model = tf.keras.models.Sequential(
        [
            tf.keras.layers.Flatten(input_shape=(28, 28)),
            tf.keras.layers.Dense(128, activation="relu"),
            tf.keras.layers.Dropout(0.2),
            tf.keras.layers.Dense(10, activation="softmax", name="output"),
        ]
    )
    model.compile(
        optimizer="adam", loss="sparse_categorical_crossentropy", metrics=["accuracy"]
    )
    model.fit(x_train, y_train, epochs=10)

    pred = model.predict(x_test[img_idx].reshape(1, 28, 28))
    print("Prob :", pred)
    print("Pred :", pred.argmax())
    print("Label:", y_test[img_idx])

    input_names = [node.op.name for node in model.inputs]
    output_names = [node.op.name for node in model.outputs]
    frozen_graph_def = tf.graph_util.convert_variables_to_constants(
        sess, sess.graph_def, output_names
    )
    with open("mnist.pb", "wb") as f:
        f.write(frozen_graph_def.SerializeToString())
    with open("mnist.pb.meta.txt", "w") as f:
        f.write(f"Input: {input_names}\n")
        f.write(f"Output: {output_names}\n")
        f.write(f"Input shape: {model.input_shape}\n")
        f.write(f"Output shape: {model.output_shape}\n")
        f.write(f"Test image index: {img_idx}\n")
        f.write(f"Test image label: {y_test[img_idx]}\n")


if __name__ == "__main__":
    main()
