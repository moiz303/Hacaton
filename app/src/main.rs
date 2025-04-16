use eframe::egui;
use email_address::EmailAddress;
fn main() -> Result<(), eframe::Error> {
    eframe::run_native(
        "Alfa Developers Qualification",
        eframe::NativeOptions::default(),
        Box::new(|_cc| Ok(Box::new(MyApp::default()))),
    )
}

#[derive(Default)]
struct MyApp {
    email: String,
    start_date: String,
    end_date: String,
    link: String,
    result: String,
}

impl eframe::App for MyApp {
    fn update(&mut self, ctx: &egui::Context, _frame: &mut eframe::Frame) {
        let mut style = (*ctx.style()).clone();
        style.text_styles = [
            (
                egui::TextStyle::Heading,
                egui::FontId::new(30.0, egui::FontFamily::Proportional),
            ),
            (
                egui::TextStyle::Body,
                egui::FontId::new(17.0, egui::FontFamily::Proportional),
            ),
            (
                egui::TextStyle::Button,
                egui::FontId::new(17.0, egui::FontFamily::Proportional),
            ),
            (
                egui::TextStyle::Monospace,
                egui::FontId::new(17.0, egui::FontFamily::Monospace),
            ),
        ]
        .into();

        style.visuals.widgets.noninteractive.corner_radius = egui::CornerRadius::same(8);
        style.visuals.widgets.inactive.corner_radius = egui::CornerRadius::same(8);
        style.visuals.widgets.hovered.corner_radius = egui::CornerRadius::same(8);
        style.visuals.widgets.active.corner_radius = egui::CornerRadius::same(8);

        ctx.set_style(style);

        egui::CentralPanel::default().show(ctx, |ui| {
            ui.add_space(20.0);
            ui.heading("Rate skills of specified developer.");
            ui.add_space(20.0);

            ui.group(|ui| {
                ui.style_mut().visuals.widgets.noninteractive.bg_fill =
                    egui::Color32::from_gray(240);
                ui.style_mut().visuals.widgets.noninteractive.corner_radius =
                    egui::CornerRadius::same(10);

                ui.vertical(|ui| {
                    ui.add_space(10.0);
                    ui.horizontal(|ui| {
                        ui.label("Email:");
                        ui.add(
                            egui::TextEdit::singleline(&mut self.email)
                                .hint_text("Enter developer's email"),
                        );
                    });
                    ui.add_space(10.0);

                    ui.horizontal(|ui| {
                        ui.label("Start Date:");
                        ui.add(
                            egui::TextEdit::singleline(&mut self.start_date)
                                .hint_text("YYYY-MM-DD"),
                        );
                    });

                    ui.horizontal(|ui| {
                        ui.label("End Date:");
                        ui.add(
                            egui::TextEdit::singleline(&mut self.end_date).hint_text("YYYY-MM-DD"),
                        );
                    });
                    ui.add_space(10.0);

                    ui.horizontal(|ui| {
                        ui.label("Link:");
                        ui.add(
                            egui::TextEdit::singleline(&mut self.link)
                                .hint_text("Enter link to repository"),
                        );
                    });

                    if ui.button("Submit").clicked() {
                        if self.email.is_empty() {
                            self.result = "Email is required.".to_string();
                            return;
                        }
                        if self.start_date.is_empty() {
                            self.result = "Start date is required.".to_string();
                            return;
                        }
                        if self.end_date.is_empty() {
                            self.result = "End date is required.".to_string();
                            return;
                        }
                        if !EmailAddress::is_valid(&self.email) {
                            self.result = "Invalid email format.".to_string();
                            return;
                        }
                        self.result = format!(
                            "Submitted Email: {}\nSubmitted Start Date: {}\nSubmitted End Date: {}",
                            self.email, self.start_date, self.end_date
                        );
                    }
                });
            });

            ui.add_space(20.0);

            ui.group(|ui| {
                ui.style_mut().visuals.override_text_color = Some(egui::Color32::WHITE);
                ui.style_mut().visuals.widgets.noninteractive.bg_fill =
                    egui::Color32::from_rgb(50, 50, 50);
                ui.style_mut().visuals.widgets.noninteractive.corner_radius =
                    egui::CornerRadius::same(10);

                ui.with_layout(
                    egui::Layout::top_down_justified(egui::Align::Center),
                    |ui| {
                        ui.add_sized(
                            ui.available_size(), // Fill all available space
                            egui::Label::new(&self.result),
                        );
                    },
                );
            });
        });
    }
}
