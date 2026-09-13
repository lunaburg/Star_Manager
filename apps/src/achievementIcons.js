import collectorIcon from "./assets/achievement-collector.png";
import archaeologistIcon from "./assets/achievement-archaeologist.png";
import doctorIcon from "./assets/achievement-doctor.png";
import organizerIcon from "./assets/achievement-organizer.png";
import perfectionistIcon from "./assets/achievement-perfectionist.png";

export const achievementIcons = {
  collector: collectorIcon,
  archaeologist: archaeologistIcon,
  doctor: doctorIcon,
  organizer: organizerIcon,
  zero_missing: perfectionistIcon
};

export function getAchievementIcon(achievement) {
  return achievementIcons[achievement?.id] || "";
}
