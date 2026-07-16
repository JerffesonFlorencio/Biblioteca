import cv2
import numpy as np
import pyautogui as pya
import time

from api.src.utils.map_path.index import IMAGE_PATH
from api.src.utils.logs.index import log


class ScreenImage:

    @staticmethod
    def get_screen_ratio():
        """
        Calcula a proporção entre a resolução atual
        e a resolução padrão 1920x1080.
        """
        screen_width, screen_height = pya.size()

        base_width = 1920
        base_height = 1080

        ratio_x = screen_width / base_width
        ratio_y = screen_height / base_height

        return ratio_x, ratio_y

    @staticmethod
    def resize_template(template, ratio_x, ratio_y):
        """
        Redimensiona o template de acordo com a escala da tela.
        """
        new_width = max(
            1,
            int(template.shape[1] * ratio_x)
        )

        new_height = max(
            1,
            int(template.shape[0] * ratio_y)
        )

        resized_template = cv2.resize(
            template,
            (new_width, new_height),
            interpolation=cv2.INTER_AREA
        )

        return resized_template

    @staticmethod
    def capture_screenshot(filename="screenshot.png"):
        """
        Captura a tela e salva em um arquivo.
        """
        screenshot = pya.screenshot()
        screenshot.save(filename)

        return filename

    @staticmethod
    def _remove_white_border(template, tolerance=245, padding=2):
        """
        Remove as margens brancas existentes ao redor da imagem.

        Isso evita que o OpenCV compare uma área branca grande
        em vez de comparar somente o ícone.
        """

        mask = np.where(
            template < tolerance,
            255,
            0
        ).astype(np.uint8)

        points = cv2.findNonZero(mask)

        if points is None:
            return template

        x, y, width, height = cv2.boundingRect(points)

        x_start = max(0, x - padding)
        y_start = max(0, y - padding)

        x_end = min(
            template.shape[1],
            x + width + padding
        )

        y_end = min(
            template.shape[0],
            y + height + padding
        )

        cropped_template = template[
            y_start:y_end,
            x_start:x_end
        ]

        return cropped_template

    @staticmethod
    def _get_search_scales():
        """
        Retorna diferentes escalas para procurar a imagem.

        Isso ajuda quando a resolução, zoom, acesso remoto ou
        escala do Windows mudam o tamanho aparente do ícone.
        """

        ratio_x, ratio_y = ScreenImage.get_screen_ratio()

        screen_ratio = (
            ratio_x + ratio_y
        ) / 2

        scales = []

        # Escalas gerais
        for scale in np.arange(0.50, 1.56, 0.05):
            scales.append(float(scale))

        # Escalas baseadas na resolução atual
        for variation in np.arange(0.75, 1.31, 0.05):
            scales.append(
                float(screen_ratio * variation)
            )

        # Remove escalas repetidas
        scales = sorted({
            round(scale, 3)
            for scale in scales
            if 0.30 <= scale <= 2.00
        })

        return scales

    @staticmethod
    def find_element_on_screen(
        element_image_path,
        threshold=0.65
    ):
        """
        Encontra um elemento na tela baseado em uma imagem.

        Retorna o mesmo formato do código anterior:

        loc, template_shape
        """

        screenshot_path = ScreenImage.capture_screenshot()

        screenshot = cv2.imread(
            screenshot_path,
            cv2.IMREAD_GRAYSCALE
        )

        template = cv2.imread(
            str(element_image_path),
            cv2.IMREAD_GRAYSCALE
        )

        if template is None:
            log.error(
                f"Erro ao carregar a imagem de referência: "
                f"{element_image_path}"
            )

            return None, None

        if screenshot is None:
            log.error(
                f"Erro ao carregar a captura de tela: "
                f"{screenshot_path}"
            )

            return None, None

        # Remove a borda branca do print
        template = ScreenImage._remove_white_border(
            template
        )

        if template.size == 0:
            log.error(
                f"A imagem ficou vazia depois de remover "
                f"a borda branca: {element_image_path}"
            )

            return None, None

        best_score = -1.0
        best_location = None
        best_template_shape = None
        best_scale = None

        scales = ScreenImage._get_search_scales()

        for scale in scales:

            new_width = int(
                template.shape[1] * scale
            )

            new_height = int(
                template.shape[0] * scale
            )

            if new_width < 5 or new_height < 5:
                continue

            if (
                new_width > screenshot.shape[1]
                or new_height > screenshot.shape[0]
            ):
                continue

            if scale < 1:
                interpolation = cv2.INTER_AREA
            else:
                interpolation = cv2.INTER_CUBIC

            resized_template = cv2.resize(
                template,
                (new_width, new_height),
                interpolation=interpolation
            )

            try:
                result = cv2.matchTemplate(
                    screenshot,
                    resized_template,
                    cv2.TM_CCOEFF_NORMED
                )

                _, max_score, _, max_location = (
                    cv2.minMaxLoc(result)
                )

                if max_score > best_score:
                    best_score = float(max_score)
                    best_location = max_location
                    best_template_shape = (
                        resized_template.shape
                    )
                    best_scale = scale

            except cv2.error as error:
                log.debug(
                    f"Erro testando escala {scale}: "
                    f"{error}"
                )

                continue

        log.info(
            f"🔎 Imagem: {element_image_path} | "
            f"Similaridade: {best_score:.3f} | "
            f"Escala: {best_scale} | "
            f"Mínimo: {threshold}"
        )

        if (
            best_location is None
            or best_template_shape is None
            or best_score < threshold
        ):
            return None, None

        best_x = best_location[0]
        best_y = best_location[1]

        # Mantém o mesmo formato do np.where
        loc = (
            np.array([best_y]),
            np.array([best_x])
        )

        return loc, best_template_shape

    @staticmethod
    def _get_element_center(
        element_image_path,
        threshold=0.65
    ):
        """
        Localiza o elemento e retorna o centro dele.
        Não executa clique.
        """

        loc, template_shape = (
            ScreenImage.find_element_on_screen(
                element_image_path,
                threshold
            )
        )

        if loc is None or template_shape is None:
            return None

        point_x = int(loc[1][0])
        point_y = int(loc[0][0])

        center_x = (
            point_x
            + template_shape[1] // 2
        )

        center_y = (
            point_y
            + template_shape[0] // 2
        )

        return center_x, center_y

    @staticmethod
    def _execute_click(
        center_x,
        center_y,
        click_type
    ):
        """
        Executa somente o clique solicitado.
        """

        normalized_click = (
            click_type.strip().lower()
            if isinstance(click_type, str)
            else ""
        )

        pya.moveTo(
            center_x,
            center_y,
            duration=0.15
        )

        if normalized_click == "right":
            pya.click(
                center_x,
                center_y,
                button="right"
            )

        elif normalized_click in (
            "double",
            "doubleclick"
        ):
            pya.doubleClick(
                center_x,
                center_y,
                interval=0.15
            )

        elif normalized_click == "click":
            pya.click(
                center_x,
                center_y
            )

        elif normalized_click in (
            "",
            "none",
            "no_click"
        ):
            log.info(
                "Imagem localizada. Nenhum clique solicitado."
            )

        else:
            log.error(
                f"Tipo de clique inválido: "
                f"'{click_type}'"
            )

            return False

        return True

    @staticmethod
    def click_element_on_screen(
        element_image_path,
        threshold=0.65
    ):
        """
        Localiza o elemento e executa um único clique esquerdo.
        """

        center = ScreenImage._get_element_center(
            element_image_path,
            threshold
        )

        if center is None:
            return False

        center_x, center_y = center

        pya.click(
            center_x,
            center_y
        )

        return True

    @staticmethod
    def click_and_drag_element(
        image_alias,
        destination_x,
        destination_y,
        threshold=0.65
    ):
        """
        Localiza um elemento e arrasta até o destino informado.
        """

        image_path = IMAGE_PATH.get(image_alias)

        if not image_path:
            log.error(
                f"Imagem '{image_alias}' "
                f"não encontrada no IMAGE_PATH."
            )

            return False

        center = ScreenImage._get_element_center(
            image_path,
            threshold
        )

        if center is None:
            return False

        center_x, center_y = center

        pya.moveTo(
            center_x,
            center_y,
            duration=0.2
        )

        pya.mouseDown(button="left")

        pya.moveTo(
            destination_x,
            destination_y,
            duration=0.5
        )

        pya.mouseUp(button="left")

        return True

    @staticmethod
    def wait_and_click(
        image_alias,
        description
    ):
        """
        Aguarda até que o elemento apareça
        e executa um clique.
        """

        log.info(
            f"⌛ Aguardando {description} "
            f"aparecer na tela..."
        )

        image_path = IMAGE_PATH.get(image_alias)

        if not image_path:
            log.error(
                f"Imagem '{image_alias}' "
                f"não encontrada no IMAGE_PATH."
            )

            return False

        while True:
            try:
                if ScreenImage.click_element_on_screen(
                    image_path
                ):
                    log.info(
                        f"✅ {description} "
                        f"encontrado e clicado."
                    )

                    time.sleep(2)
                    return True

            except Exception as error:
                log.warning(
                    f"Erro procurando {description}: "
                    f"{error}"
                )

            time.sleep(0.5)

    @staticmethod
    def wait_and_Doubleclick(
        image_alias,
        description
    ):
        """
        Aguarda até que o elemento apareça
        e executa exatamente um clique duplo.
        """

        log.info(
            f"⌛ Aguardando {description} "
            f"aparecer na tela..."
        )

        image_path = IMAGE_PATH.get(image_alias)

        if not image_path:
            log.error(
                f"Imagem '{image_alias}' "
                f"não encontrada no IMAGE_PATH."
            )

            return False

        while True:
            try:
                center = (
                    ScreenImage._get_element_center(
                        image_path
                    )
                )

                if center is not None:
                    center_x, center_y = center

                    pya.doubleClick(
                        center_x,
                        center_y,
                        interval=0.15
                    )

                    log.info(
                        f"✅ {description} encontrado "
                        f"e clicado duas vezes."
                    )

                    time.sleep(2)
                    return True

            except Exception as error:
                log.warning(
                    f"Erro procurando {description}: "
                    f"{error}"
                )

            time.sleep(0.5)

    @staticmethod
    def find_img(
        image_alias,
        description,
        click_type,
        timeout=8
    ):
        """
        Aguarda até que o elemento apareça,
        executando o tipo de clique solicitado.
        """

        log.info(
            f"⌛ Aguardando {description} aparecer "
            f"na tela. Tempo limite: {timeout}s..."
        )

        image_path = IMAGE_PATH.get(image_alias)
        start_time = time.time()

        if not image_path:
            log.error(
                f"Imagem '{image_alias}' "
                f"não encontrada no IMAGE_PATH."
            )

            return False

        while time.time() - start_time <= timeout:
            try:
                center = (
                    ScreenImage._get_element_center(
                        image_path
                    )
                )

                if center is not None:
                    center_x, center_y = center

                    clicked = ScreenImage._execute_click(
                        center_x,
                        center_y,
                        click_type
                    )

                    if not clicked:
                        return False

                    log.info(
                        f"✅ {description} encontrado."
                    )

                    time.sleep(2)
                    return True

            except Exception as error:
                log.warning(
                    f"🚨 Erro procurando "
                    f"{description}: {error}"
                )

            time.sleep(0.5)

        log.warning(
            f"⏳ Tempo limite de {timeout}s "
            f"atingido! {description} "
            f"não encontrado."
        )

        return False

    @staticmethod
    def find_img_busc(
        image_alias,
        description,
        click_type,
        timeout=60
    ):
        """
        Mesma busca do find_img, mas com
        tempo padrão de 60 segundos.
        """

        return ScreenImage.find_img(
            image_alias=image_alias,
            description=description,
            click_type=click_type,
            timeout=timeout
        )
